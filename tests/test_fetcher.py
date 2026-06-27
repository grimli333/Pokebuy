from pokebuy.collectors.fetcher import is_blocked_response


def test_detects_datadome_blocked_page_without_403() -> None:
    assert is_blocked_response(
        200,
        {},
        "<html>Please enable JavaScript<script src='https://ct.captcha-delivery.com/c.js'></script>",
    )
