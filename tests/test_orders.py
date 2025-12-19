import os
os.environ['DISABLE_USER_CHECK']='true'
import asyncio
from fastapi.testclient import TestClient
from service_users.app.main import app as users_app
from service_orders.app.main import app as orders_app

users = TestClient(users_app)
orders = TestClient(orders_app)

def _register_and_token(email="buyer@example.com"):
    users.post("/v1/users/register", json={"email":email,"password":"password123","name":"Buyer"})
    r = users.post("/v1/users/login", json={"email":email,"password":"password123"})
    return r.json()["data"]["token"]

def test_create_and_list_orders():
    token = _register_and_token()

    r = orders.post("/v1/orders", json={"items":[{"product":"bricks","quantity":2}],"total_sum":100.0},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    order_id = r.json()["data"]["id"]
    assert r.json()["data"]["status"] == "created"

    r2 = orders.get(f"/v1/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200

    r3 = orders.get("/v1/orders?page=1&page_size=10", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json()["data"]["total"] >= 1

def test_update_other_users_order_forbidden():
    token1 = _register_and_token("a@example.com")
    token2 = _register_and_token("b@example.com")

    r = orders.post("/v1/orders", json={"items":[{"product":"cement","quantity":1}],"total_sum":50.0},
                    headers={"Authorization": f"Bearer {token1}"})
    order_id = r.json()["data"]["id"]

    r2 = orders.patch(f"/v1/orders/{order_id}/status", json={"status":"completed"},
                      headers={"Authorization": f"Bearer {token2}"})
    assert r2.status_code == 403

def test_cancel_own_order():
    token = _register_and_token("c@example.com")
    r = orders.post("/v1/orders", json={"items":[{"product":"paint","quantity":3}],"total_sum":30.0},
                    headers={"Authorization": f"Bearer {token}"})
    order_id = r.json()["data"]["id"]

    r2 = orders.post(f"/v1/orders/{order_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "cancelled"
