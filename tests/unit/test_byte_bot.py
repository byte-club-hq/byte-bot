from byte_bot.byte_bot import health_check

def test_health_check_returns_ok_status():
    result = health_check()
    assert result == {"status": "ok", "service": "byte_bot"}
