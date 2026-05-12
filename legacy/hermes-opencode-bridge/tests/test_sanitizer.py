from hermes_opencode_bridge.sanitizer import sanitize_text


def test_sanitize_authorization_bearer() -> None:
    text = "Authorization: Bearer supersecret"
    assert sanitize_text(text) == "Authorization: Bearer [REDACTED]"


def test_sanitize_api_key() -> None:
    text = "api_key=abc123"
    assert "abc123" not in sanitize_text(text)
