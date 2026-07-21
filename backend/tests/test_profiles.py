from tests.conftest import API


async def _create_client(client, auth_headers, email="p@example.com"):
    resp = await client.post(f"{API}/clients", json={"full_name": "P", "email": email}, headers=auth_headers)
    return resp.json()["id"]


async def test_create_and_list_profile(client, auth_headers):
    client_id = await _create_client(client, auth_headers)

    resp = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "A", "raw_text": "Python engineer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    profile_id = resp.json()["id"]

    resp = await client.get(f"{API}/profiles", params={"client_id": client_id}, headers=auth_headers)
    assert resp.status_code == 200
    assert any(p["id"] == profile_id for p in resp.json())


async def test_profile_scoped_to_owning_bd(client, auth_headers):
    client_id = await _create_client(client, auth_headers, email="p2@example.com")
    profile_resp = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "A"},
        headers=auth_headers,
    )
    profile_id = profile_resp.json()["id"]

    await client.post(
        f"{API}/auth/register",
        json={"email": "other-profile@example.com", "password": "testpass123", "full_name": "Other"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": "other-profile@example.com", "password": "testpass123"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get(f"{API}/profiles/{profile_id}", headers=other_headers)
    assert resp.status_code == 404
