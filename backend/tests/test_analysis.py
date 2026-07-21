from tests.conftest import API


async def _create_client_with_profiles(client, auth_headers, email):
    client_resp = await client.post(f"{API}/clients", json={"full_name": "C", "email": email}, headers=auth_headers)
    client_id = client_resp.json()["id"]

    p1 = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "A", "raw_text": "strong profile"},
        headers=auth_headers,
    )
    p2 = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "B", "raw_text": "weak profile"},
        headers=auth_headers,
    )
    return client_id, p1.json()["id"], p2.json()["id"]


async def test_keyword_analysis(client, auth_headers, mock_llm):
    client_id, profile_id, _ = await _create_client_with_profiles(client, auth_headers, "kw@example.com")

    resp = await client.post(f"{API}/analysis/keywords", json={"profile_id": profile_id}, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["ats_score"] == 80
    assert body["missing_keywords"] == ["aws"]


async def test_location_analysis(client, auth_headers, mock_llm):
    client_id, _, _ = await _create_client_with_profiles(client, auth_headers, "loc@example.com")

    resp = await client.post(f"{API}/analysis/location", json={"client_id": client_id}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["location_penalty_score"] == 50


async def test_compare_profiles(client, auth_headers, mock_llm):
    client_id, p1_id, p2_id = await _create_client_with_profiles(client, auth_headers, "cmp@example.com")

    resp = await client.post(
        f"{API}/analysis/compare",
        json={"client_id": client_id, "profile_ids": [p1_id, p2_id]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "complete"
    assert len(body["result_detail"]["profile_scores"]) == 2

    get_resp = await client.get(f"{API}/analysis/comparisons/{body['id']}", headers=auth_headers)
    assert get_resp.status_code == 200


async def test_compare_requires_at_least_two_profiles(client, auth_headers, mock_llm):
    client_id, p1_id, _ = await _create_client_with_profiles(client, auth_headers, "cmp2@example.com")

    resp = await client.post(
        f"{API}/analysis/compare",
        json={"client_id": client_id, "profile_ids": [p1_id]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
