from sqlmodel import select

from db.models import ClientDocument
from tests.conftest import API


async def _create_client(client, auth_headers, email: str) -> str:
    resp = await client.post(f"{API}/clients", json={"full_name": "Doc Client", "email": email}, headers=auth_headers)
    return resp.json()["id"]


async def test_upload_and_list_document(client, auth_headers, mock_s3):
    client_id = await _create_client(client, auth_headers, "doc-upload@example.com")

    upload_resp = await client.post(
        f"{API}/clients/{client_id}/documents",
        headers=auth_headers,
        files={"file": ("passport.png", b"fake-image-bytes", "image/png")},
    )
    assert upload_resp.status_code == 201
    body = upload_resp.json()
    assert body["filename"] == "passport.png"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(b"fake-image-bytes")
    assert body["preview_url"].startswith("https://fake-s3.test/")

    list_resp = await client.get(f"{API}/clients/{client_id}/documents", headers=auth_headers)
    assert list_resp.status_code == 200
    documents = list_resp.json()
    assert len(documents) == 1
    assert documents[0]["id"] == body["id"]

    # The uploaded bytes actually landed in the (fake) S3 store, not just the DB row.
    assert len(mock_s3) == 1


async def test_document_size_limit_rejected(client, auth_headers, mock_s3, monkeypatch):
    monkeypatch.setattr("services.client_document_service.MAX_DOCUMENT_SIZE_BYTES", 10)
    client_id = await _create_client(client, auth_headers, "doc-toolarge@example.com")

    resp = await client.post(
        f"{API}/clients/{client_id}/documents",
        headers=auth_headers,
        files={"file": ("big.pdf", b"x" * 100, "application/pdf")},
    )
    assert resp.status_code == 413
    assert len(mock_s3) == 0


async def test_delete_document(client, auth_headers, mock_s3):
    client_id = await _create_client(client, auth_headers, "doc-delete@example.com")

    upload_resp = await client.post(
        f"{API}/clients/{client_id}/documents",
        headers=auth_headers,
        files={"file": ("contract.pdf", b"contract-bytes", "application/pdf")},
    )
    document_id = upload_resp.json()["id"]
    assert len(mock_s3) == 1

    delete_resp = await client.delete(f"{API}/clients/documents/{document_id}", headers=auth_headers)
    assert delete_resp.status_code == 204
    assert len(mock_s3) == 0

    list_resp = await client.get(f"{API}/clients/{client_id}/documents", headers=auth_headers)
    assert list_resp.json() == []


async def test_document_access_is_bd_scoped(client, auth_headers, mock_s3):
    client_id = await _create_client(client, auth_headers, "doc-scoped@example.com")
    upload_resp = await client.post(
        f"{API}/clients/{client_id}/documents",
        headers=auth_headers,
        files={"file": ("id.png", b"id-bytes", "image/png")},
    )
    document_id = upload_resp.json()["id"]

    await client.post(
        f"{API}/auth/register",
        json={"email": "other-doc-bd@example.com", "password": "testpass123", "full_name": "Other"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": "other-doc-bd@example.com", "password": "testpass123"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert (await client.get(f"{API}/clients/{client_id}/documents", headers=other_headers)).status_code == 404
    assert (await client.delete(f"{API}/clients/documents/{document_id}", headers=other_headers)).status_code == 404


async def test_client_delete_removes_documents_from_s3_and_db(client, auth_headers, mock_s3, db_session):
    client_id = await _create_client(client, auth_headers, "doc-cascade@example.com")
    await client.post(
        f"{API}/clients/{client_id}/documents",
        headers=auth_headers,
        files={"file": ("resume-scan.pdf", b"resume-bytes", "application/pdf")},
    )
    assert len(mock_s3) == 1

    delete_resp = await client.delete(f"{API}/clients/{client_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    assert len(mock_s3) == 0
    remaining = (await db_session.exec(select(ClientDocument))).all()
    assert remaining == []
