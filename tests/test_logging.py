import json
import logging
from pathlib import Path

from pokebuy.logging import configure_logging, get_logger


def test_configure_logging_can_write_json_to_file(tmp_path: Path) -> None:
    log_path = tmp_path / "pokebuy.log"

    configure_logging("INFO", log_file_enabled=True, log_file_path=log_path)
    get_logger("pokebuy.tests").info("file_logging_test", answer=42)

    logging.shutdown()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[-1])

    assert payload["event"] == "file_logging_test"
    assert payload["answer"] == 42


def test_logger_created_before_configuration_uses_file_handler(tmp_path: Path) -> None:
    log_path = tmp_path / "pokebuy.log"
    logger = get_logger("pokebuy.tests.preconfigured")

    configure_logging("INFO", log_file_enabled=True, log_file_path=log_path)
    logger.info("preconfigured_file_logging_test", answer=43)

    logging.shutdown()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[-1])

    assert payload["event"] == "preconfigured_file_logging_test"
    assert payload["answer"] == 43
