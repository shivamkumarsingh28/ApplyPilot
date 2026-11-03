def test_private_network_preflight_is_answered(client):
    """Chrome Private Network Access: localhost page -> localhost API preflight must not fail."""
    r = client.options("/api/v1/auth/register", headers={
        "Origin": "http://localhost:3123", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type", "Access-Control-Request-Private-Network": "true"})
    assert r.status_code == 200, r.text
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3123"


def test_dev_cors_allows_any_localhost_port(client):
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:3011"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3011"
    r2 = client.get("/api/v1/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r2.headers
