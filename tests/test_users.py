from fastapi.testclient import TestClient
from service_users.app.main import app as users_app

client = TestClient(users_app)

def test_register_and_login_and_me():
    r = client.post("/v1/users/register", json={"email":"u1@example.com","password":"password123","name":"User One"})
    assert r.status_code == 200
    assert r.json()["success"] is True
    user_id = r.json()["data"]["id"]

    r2 = client.post("/v1/users/login", json={"email":"u1@example.com","password":"password123"})
    assert r2.status_code == 200
    token = r2.json()["data"]["token"]
    assert token

    r3 = client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json()["data"]["id"] == user_id

def test_duplicate_email():
    client.post("/v1/users/register", json={"email":"dup@example.com","password":"password123","name":"A"})
    r = client.post("/v1/users/register", json={"email":"dup@example.com","password":"password123","name":"B"})
    assert r.status_code == 409
    assert r.json()["success"] is False
