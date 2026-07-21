from tests.conftest import API


async def test_create_and_list_client(client, auth_headers):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane@example.com"}, headers=auth_headers
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    resp = await client.get(f"{API}/clients", headers=auth_headers)
    assert resp.status_code == 200
    assert any(c["id"] == client_id for c in resp.json())


async def test_cross_bd_client_access_is_scoped(client, auth_headers):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane2@example.com"}, headers=auth_headers
    )
    client_id = resp.json()["id"]

    await client.post(
        f"{API}/auth/register",
        json={"email": "other@example.com", "password": "testpass123", "full_name": "Other"},
    )
    login = await client.post(f"{API}/auth/login", json={"email": "other@example.com", "password": "testpass123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get(f"{API}/clients/{client_id}", headers=other_headers)
    assert resp.status_code == 404

    resp = await client.get(f"{API}/clients", headers=other_headers)
    assert resp.json() == []


async def test_target_role_create_and_list(client, auth_headers):
    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane3@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]

    resp = await client.post(
        f"{API}/clients/{client_id}/target-roles",
        json={"title": "Backend Engineer", "must_have_keywords": ["python", "fastapi"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["must_have_keywords"] == ["python", "fastapi"]

    resp = await client.get(f"{API}/clients/{client_id}/target-roles", headers=auth_headers)
    assert len(resp.json()) == 1
