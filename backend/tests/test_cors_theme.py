def test_dev_cors_allows_any_localhost_port(client):
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:3011"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3011"
    r2 = client.get("/api/v1/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r2.headers
