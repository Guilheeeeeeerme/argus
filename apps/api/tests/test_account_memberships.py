"""Membership selection, revocation and zero-account account regressions."""

import uuid

import pytest

from argus.domain.enums import UserRole
from tests.helpers import bearer, session_token


@pytest.mark.asyncio
async def test_membership_lifecycle(admin_client):
    client = admin_client
    platform = bearer(await session_token(UserRole.ROOT))
    accounts = []
    user_id = None
    try:
        for suffix in ("one", "two", "outside"):
            response = await client.post("/v1/admin/accounts", headers=platform,
                json={"name": suffix, "slug": f"membership-{suffix}-{uuid.uuid4().hex}"})
            assert response.status_code == 201
            accounts.append(response.json()["id"])
        email = f"membership-{uuid.uuid4().hex}@example.com"
        response = await client.post("/v1/admin/users", headers=platform,
            json={"email": email, "password": "Password123!", "role": "operator", "account_ids": []})
        assert response.status_code == 201
        user_id = response.json()["id"]
        assert response.json()["account_ids"] == []
        login = await client.post("/v1/auth/login", json={"email": email, "password": "Password123!"})
        assert login.status_code == 200
        member = bearer(login.json()["token"])
        assert login.json()["activeAccount"] is None
        assert (await client.get("/v1/auth/accounts", headers=member)).json() == []
        denied = await client.patch("/v1/auth/context", headers=member, json={"accountId": accounts[0]})
        assert denied.status_code == 403

        assigned = await client.patch(f"/v1/admin/users/{user_id}", headers=platform,
            json={"account_ids": accounts[:2]})
        assert assigned.status_code == 200
        assert set(assigned.json()["account_ids"]) == set(accounts[:2])
        visible = await client.get("/v1/auth/accounts", headers=member)
        assert {item["id"] for item in visible.json()} == set(accounts[:2])
        for account_id in accounts[:2]:
            selected = await client.patch("/v1/auth/context", headers=member, json={"accountId": account_id})
            assert selected.status_code == 200
            assert selected.json()["activeAccount"]["id"] == account_id
        denied = await client.patch("/v1/auth/context", headers=member, json={"accountId": accounts[2]})
        assert denied.status_code == 403
        assert (await client.get(f"/v1/accounts/{accounts[0]}/units", headers=member)).status_code == 403

        await client.patch(f"/v1/admin/users/{user_id}", headers=platform, json={"account_ids": [accounts[0]]})
        assert (await client.get(f"/v1/accounts/{accounts[1]}/units", headers=member)).status_code == 403
        me = await client.get("/v1/auth/me", headers=member)
        assert me.status_code == 200
        assert me.json()["activeAccount"] is None
        selected = await client.patch("/v1/auth/context", headers=member, json={"accountId": accounts[0]})
        assert selected.status_code == 200
        cleared = await client.patch("/v1/auth/context", headers=member, json={"accountId": None})
        assert cleared.status_code == 400
        assert selected.json()["activeAccount"]["id"] == accounts[0]
        me_after_clear = await client.get("/v1/auth/me", headers=member)
        assert me_after_clear.status_code == 200
        assert me_after_clear.json()["activeAccount"]["id"] == accounts[0]
        malformed = await client.patch("/v1/auth/context", headers=member, json={"accountId": "invalid"})
        assert malformed.status_code == 422
        # Removing a primary account must preserve the account and its other memberships.
        await client.patch(f"/v1/admin/users/{user_id}", headers=platform, json={"account_ids": accounts[:2]})
        await client.delete(f"/v1/admin/accounts/{accounts[0]}", headers=platform)
        login = await client.post("/v1/auth/login", json={"email": email, "password": "Password123!"})
        assert login.status_code == 200
        assert login.json()["activeAccount"]["id"] == accounts[1]
    finally:
        if user_id:
            await client.delete(f"/v1/admin/users/{user_id}", headers=platform)
        for account_id in accounts:
            await client.delete(f"/v1/admin/accounts/{account_id}", headers=platform)
