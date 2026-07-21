from tests.conftest import API


async def test_register_and_login(client):
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": "testpass123", "full_name": "A"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert body["role"] == "bd"

    resp = await client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client):
    await client.post(
        f"{API}/auth/register",
        json={"email": "b@example.com", "password": "testpass123", "full_name": "B"},
    )
    resp = await client.post(f"{API}/auth/login", json={"email": "b@example.com", "password": "wrong"})
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get(f"{API}/bds/me")
    assert resp.status_code == 401


async def test_duplicate_registration_conflicts(client):
    payload = {"email": "dup@example.com", "password": "testpass123", "full_name": "D"}
    await client.post(f"{API}/auth/register", json=payload)
    resp = await client.post(f"{API}/auth/register", json=payload)
    assert resp.status_code == 409
