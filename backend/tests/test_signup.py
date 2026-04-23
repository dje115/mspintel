def test_signup_creates_tenant_and_membership(client, db_session):
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Signup User",
            "email": "signup-user@example.com",
            "password": "ChangeMe123!",
            "tenant_name": "Signup Tenant",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["refresh_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert len(me.json()["memberships"]) == 1
