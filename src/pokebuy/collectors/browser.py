import json
import os
import socket
import subprocess
import sys
import tempfile
import time

import websocket
from curl_cffi import requests as curl_requests

from pokebuy.collectors.fetcher import FetchResult, is_blocked_response
from pokebuy.config import Settings
from pokebuy.models import FetchStatus


def find_chrome() -> str:
    """Locate the Google Chrome or Chromium executable on the current system."""
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]

    if sys.platform == "darwin":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            os.path.expanduser("~/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
    elif sys.platform.startswith("win"):
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            ) as key:
                path, _ = winreg.QueryValueEx(key, "")
                if os.path.exists(path):
                    return str(path)
        except OSError:
            pass
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
    else:
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
        for p in paths:
            if os.path.exists(p):
                return p

    raise FileNotFoundError(
        "Google Chrome or Chromium executable not found. "
        "Please set CHROME_PATH environment variable."
    )


def find_free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ChromeLauncher:
    """Context manager for launching a normal Chrome browser with remote debugging."""

    def __init__(self, settings: Settings, headless: bool, use_persistent_profile: bool) -> None:
        self.settings = settings
        self.headless = headless
        self.use_persistent_profile = use_persistent_profile
        self.proc: subprocess.Popen[bytes] | None = None
        self.temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.port: int | None = None

    def __enter__(self) -> "ChromeLauncher":
        chrome_path = find_chrome()
        self.port = find_free_port()

        if self.use_persistent_profile:
            self.settings.browser_profile_dir.mkdir(parents=True, exist_ok=True)
            user_data_dir = str(self.settings.browser_profile_dir)
        else:
            self.temp_dir = tempfile.TemporaryDirectory()
            user_data_dir = self.temp_dir.name

        args = [
            chrome_path,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={user_data_dir}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-dev-shm-usage",
            "--disable-domain-reliability",
            "--disable-extensions",
            "--disable-features=AudioServiceOutOfProcess",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-notifications",
            "--disable-offer-store-unmasked-wallet-cards",
            "--disable-popup-blocking",
            "--disable-print-preview",
            "--disable-prompt-on-repost",
            "--disable-renderer-backgrounding",
            "--disable-setuid-sandbox",
            "--disable-speech-api",
            "--disable-sync",
            "--hide-scrollbars",
            "--ignore-gpu-blocklist",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-gesture-requirement",
            "--password-store=basic",
            "--use-mock-keychain",
        ]
        if self.headless:
            args.append("--headless=new")

        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for port to be ready
        start_time = time.time()
        connected = False
        while time.time() - start_time < 15.0:
            try:
                r = curl_requests.get(f"http://127.0.0.1:{self.port}/json/version", timeout=1.0)
                if r.status_code == 200:
                    connected = True
                    break
            except Exception:
                pass
            time.sleep(0.1)

        if not connected:
            self.close()
            raise RuntimeError("Failed to start or connect to Chrome browser within timeout.")

        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except Exception:
                pass
            self.temp_dir = None


class CDPClient:
    """A simple synchronous client to communicate with Chrome over DevTools Protocol."""

    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self.ws = websocket.create_connection(ws_url, timeout=10.0)
        self.next_id = 1

    def send_command(self, method: str, params: dict[str, object] | None = None) -> int:
        cmd_id = self.next_id
        self.next_id += 1
        payload = {
            "id": cmd_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        self.ws.send(json.dumps(payload))
        return cmd_id

    def wait_for_response(self, cmd_id: int, timeout_seconds: float = 10.0) -> dict[str, object]:
        start_time = time.time()
        self.ws.settimeout(timeout_seconds)
        while time.time() - start_time < timeout_seconds:
            try:
                msg_str = self.ws.recv()
                if not msg_str:
                    continue
                msg = json.loads(msg_str)
                if msg.get("id") == cmd_id:
                    return dict(msg)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break
        raise TimeoutError(f"Timeout waiting for response to command {cmd_id}")

    def execute(
        self,
        method: str,
        params: dict[str, object] | None = None,
        timeout_seconds: float = 10.0,
    ) -> dict[str, object]:
        cmd_id = self.send_command(method, params)
        resp = self.wait_for_response(cmd_id, timeout_seconds)
        if "error" in resp:
            raise RuntimeError(f"CDP Error in {method}: {resp['error']}")
        return dict(resp.get("result", {}))  # type: ignore

    def evaluate(self, expression: str, timeout_seconds: float = 10.0) -> object:
        result = self.execute(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
            timeout_seconds=timeout_seconds,
        )
        if "exceptionDetails" in result:
            raise RuntimeError(f"JS Exception: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")  # type: ignore

    def navigate_and_wait(
        self,
        url: str,
        timeout_seconds: float = 45.0,
    ) -> tuple[int | None, dict[str, str], str]:
        """Navigate to a URL and wait for load and network events to settle."""
        self.execute("Network.enable")
        self.execute("Page.enable")

        nav_cmd_id = self.send_command("Page.navigate", {"url": url})

        start_time = time.time()
        main_document_response = None
        load_fired = False

        self.ws.settimeout(1.0)
        while time.time() - start_time < timeout_seconds:
            try:
                msg_str = self.ws.recv()
                if not msg_str:
                    time.sleep(0.05)
                    continue
                msg = json.loads(msg_str)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break

            method = msg.get("method")
            params = msg.get("params", {})
            msg_id = msg.get("id")

            if msg_id == nav_cmd_id:
                if "error" in msg:
                    # Navigation itself reported an error
                    pass

            if method == "Network.responseReceived":
                resp_type = params.get("type")
                response = params.get("response", {})
                if resp_type == "Document":
                    main_document_response = response

            if method == "Page.loadEventFired":
                load_fired = True
                break

        # Fallback load state checking
        if not load_fired:
            poll_start = time.time()
            while time.time() - poll_start < 10.0:
                try:
                    state = self.evaluate("document.readyState")
                    if state == "complete":
                        load_fired = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)

        final_url = url
        try:
            val = self.evaluate("document.location.href")
            if isinstance(val, str):
                final_url = val
        except Exception:
            pass

        status_code = None
        headers = {}
        if main_document_response:
            status_code = main_document_response.get("status")
            headers = main_document_response.get("headers", {})
            headers = {str(k): str(v) for k, v in headers.items()}

        return status_code, headers, final_url

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


class PokemonCenterBrowserFetcher:
    """Fetcher that uses a normal Google Chrome browser via CDP and DevTools protocol."""

    def __init__(
        self,
        settings: Settings,
        *,
        headless: bool | None = None,
        manual_wait_seconds: float | None = None,
        use_persistent_profile: bool = False,
    ) -> None:
        self._settings = settings
        self._headless = settings.browser_headless if headless is None else headless
        self._manual_wait_seconds = (
            settings.browser_manual_wait_seconds
            if manual_wait_seconds is None
            else manual_wait_seconds
        )
        self._use_persistent_profile = use_persistent_profile

    def fetch(self, url: str) -> FetchResult:
        timeout_seconds = self._settings.browser_timeout_seconds

        try:
            with ChromeLauncher(
                self._settings, self._headless, self._use_persistent_profile
            ) as launcher:
                # 1. Create a new blank tab
                resp = curl_requests.put(f"http://127.0.0.1:{launcher.port}/json/new", timeout=5.0)
                tab_data = json.loads(resp.text)
                tab_id = tab_data["id"]
                ws_url = tab_data["webSocketDebuggerUrl"]

                # 2. Connect to tab websocket
                client = CDPClient(ws_url)
                try:
                    # 3. Navigate and wait for load
                    status_code, headers, final_url = client.navigate_and_wait(
                        url, timeout_seconds=timeout_seconds
                    )

                    # 4. Manual wait if needed
                    if self._manual_wait_seconds > 0:
                        time.sleep(self._manual_wait_seconds)

                    # 5. Extract HTML
                    try:
                        html_val = client.evaluate("document.documentElement.outerHTML")
                        html = str(html_val) if html_val is not None else ""
                    except Exception:
                        html = ""

                    # 6. Extract final URL in case it changed
                    try:
                        href_val = client.evaluate("document.location.href")
                        if isinstance(href_val, str):
                            final_url = href_val
                    except Exception:
                        pass
                finally:
                    client.close()
                    # 7. Close the tab
                    try:
                        curl_requests.get(
                            f"http://127.0.0.1:{launcher.port}/json/close/{tab_id}", timeout=5.0
                        )
                    except Exception:
                        pass
        except Exception as exc:
            return FetchResult(
                url=url,
                status_code=None,
                text="",
                fetch_status=FetchStatus.ERROR,
                fetch_error=f"browser fetch failed: {exc}",
                headers={},
            )

        if status_code == 404:
            return FetchResult(
                url=final_url,
                status_code=status_code,
                text=html,
                fetch_status=FetchStatus.NOT_FOUND,
                fetch_error="product page returned 404",
                headers=headers,
            )
        if status_code is not None and is_blocked_response(status_code, headers, html):
            return FetchResult(
                url=final_url,
                status_code=status_code,
                text=html,
                fetch_status=FetchStatus.BLOCKED,
                fetch_error="Pokemon Center returned bot-protection or CAPTCHA HTML",
                headers=headers,
            )
        if status_code is not None and status_code >= 400:
            return FetchResult(
                url=final_url,
                status_code=status_code,
                text=html,
                fetch_status=FetchStatus.ERROR,
                fetch_error=f"product page returned HTTP {status_code}",
                headers=headers,
            )
        return FetchResult(
            url=final_url,
            status_code=status_code or 200,
            text=html,
            fetch_status=FetchStatus.SUCCESS,
            fetch_error=None,
            headers=headers,
        )


def warm_pokemon_center_session(
    settings: Settings,
    *,
    url: str,
    headless: bool | None = None,
    manual_wait_seconds: float = 300.0,
) -> str:
    headless_value = settings.browser_headless if headless is None else headless
    settings.browser_profile_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_state_dir.mkdir(parents=True, exist_ok=True)
    storage_state_path = settings.browser_state_dir / "pokemon-center-storage-state.json"

    try:
        with ChromeLauncher(settings, headless_value, use_persistent_profile=True) as launcher:
            # Open tab and navigate to url
            resp = curl_requests.put(f"http://127.0.0.1:{launcher.port}/json/new", timeout=5.0)
            tab_data = json.loads(resp.text)
            tab_id = tab_data["id"]
            ws_url = tab_data["webSocketDebuggerUrl"]

            client = CDPClient(ws_url)
            try:
                # Start navigation
                client.navigate_and_wait(url, timeout_seconds=settings.browser_timeout_seconds)

                # Wait for user input / manual wait
                if manual_wait_seconds > 0:
                    time.sleep(manual_wait_seconds)

                # Extract cookies via CDP
                cookies_result = client.execute("Network.getAllCookies")
                cookies = cookies_result.get("cookies", [])

                formatted_cookies = []
                for cookie in cookies:  # type: ignore
                    formatted_cookies.append(
                        {
                            "name": cookie.get("name"),
                            "value": cookie.get("value"),
                            "domain": cookie.get("domain"),
                            "path": cookie.get("path"),
                            "expires": cookie.get("expires"),
                            "httpOnly": cookie.get("httpOnly"),
                            "secure": cookie.get("secure"),
                            "sameSite": cookie.get("sameSite", "Lax"),
                        }
                    )

                # Extract localStorage via JS evaluation
                local_storage_raw = {}
                try:
                    local_storage_str = client.evaluate("JSON.stringify(window.localStorage)")
                    if isinstance(local_storage_str, str):
                        local_storage_raw = json.loads(local_storage_str)
                except Exception:
                    pass

                formatted_local_storage = []
                for k, v in local_storage_raw.items():
                    formatted_local_storage.append(
                        {
                            "name": k,
                            "value": str(v),
                        }
                    )

                storage_state = {
                    "cookies": formatted_cookies,
                    "origins": [
                        {
                            "origin": url,
                            "localStorage": formatted_local_storage,
                        }
                    ],
                }

                with open(storage_state_path, "w", encoding="utf-8") as f:
                    json.dump(storage_state, f, indent=2)
            finally:
                client.close()
                try:
                    curl_requests.get(
                        f"http://127.0.0.1:{launcher.port}/json/close/{tab_id}", timeout=5.0
                    )
                except Exception:
                    pass
    except Exception as exc:
        return f"session warm failed: {exc}"

    return (
        f"saved browser profile at {settings.browser_profile_dir}; "
        f"storage state at {storage_state_path}"
    )
