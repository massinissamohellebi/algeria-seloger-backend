"""Router-level tests for the epic-8 auth flows: email verification,
forgot/reset password, refresh/logout rotation and login rate-limiting."""

import pytest

REGISTER = {
    "email": "flow@example.com",
    "password": "supersecret123",
    "full_name": "Flow User",
}


async def _register(client, mailer, **overrides):
    payload = {**REGISTER, **overrides}
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return payload


async def _register_and_verify(client, mailer, **overrides):
    """Register then confirm the email so the account can sign in."""
    payload = await _register(client, mailer, **overrides)
    await client.post("/auth/verify-email", json={"token": mailer.last_token()})
    return payload


async def _login(client, email, password):
    return await client.post(
        "/auth/login", json={"email": email, "password": password}
    )


# --- Email verification (Story 2) ------------------------------------------


@pytest.mark.asyncio
async def test_register_sends_verification_email(client, mailer):
    await _register(client, mailer)
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["to"] == REGISTER["email"]
    assert "vérif" in mailer.sent[0]["subject"].lower()


@pytest.mark.asyncio
async def test_verify_email_marks_user_verified(client, mailer):
    await _register(client, mailer)
    token = mailer.last_token()

    resp = await client.post("/auth/verify-email", json={"token": token})
    assert resp.status_code == 200

    login = await _login(client, REGISTER["email"], REGISTER["password"])
    access = login.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.json()["is_email_verified"] is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token_returns_400(client, mailer):
    await _register(client, mailer)
    resp = await client.post("/auth/verify-email", json={"token": "garbage"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_verification_token"


@pytest.mark.asyncio
async def test_verify_email_token_is_single_use(client, mailer):
    await _register(client, mailer)
    token = mailer.last_token()
    assert (await client.post("/auth/verify-email", json={"token": token})).status_code == 200
    reuse = await client.post("/auth/verify-email", json={"token": token})
    assert reuse.status_code == 400


@pytest.mark.asyncio
async def test_resend_verification_is_enumeration_safe(client, mailer):
    resp = await client.post(
        "/auth/resend-verification", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200
    assert mailer.sent == []  # no email for an unknown address


@pytest.mark.asyncio
async def test_resend_verification_issues_new_working_token(client, mailer):
    await _register(client, mailer)
    resp = await client.post(
        "/auth/resend-verification", json={"email": REGISTER["email"]}
    )
    assert resp.status_code == 200
    assert len(mailer.sent) == 2
    token = mailer.last_token()
    assert (await client.post("/auth/verify-email", json={"token": token})).status_code == 200


# --- Forgot / reset password (Story 3) -------------------------------------


@pytest.mark.asyncio
async def test_forgot_password_always_200_even_for_unknown(client, mailer):
    resp = await client.post(
        "/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert resp.status_code == 200
    assert mailer.sent == []


@pytest.mark.asyncio
async def test_forgot_then_reset_password_updates_credentials(client, mailer):
    await _register_and_verify(client, mailer)
    await client.post("/auth/forgot-password", json={"email": REGISTER["email"]})
    token = mailer.last_token()

    resp = await client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "brandnew-pass-9"},
    )
    assert resp.status_code == 200

    assert (await _login(client, REGISTER["email"], "brandnew-pass-9")).status_code == 200
    assert (await _login(client, REGISTER["email"], REGISTER["password"])).status_code == 401


@pytest.mark.asyncio
async def test_reset_password_invalid_token_returns_400(client, mailer):
    resp = await client.post(
        "/auth/reset-password",
        json={"token": "nope", "new_password": "brandnew-pass-9"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_reset_token"


@pytest.mark.asyncio
async def test_reset_password_is_single_use(client, mailer):
    await _register(client, mailer)
    await client.post("/auth/forgot-password", json={"email": REGISTER["email"]})
    token = mailer.last_token()
    body = {"token": token, "new_password": "brandnew-pass-9"}
    assert (await client.post("/auth/reset-password", json=body)).status_code == 200
    assert (await client.post("/auth/reset-password", json=body)).status_code == 400


@pytest.mark.asyncio
async def test_reset_password_revokes_active_refresh_tokens(client, mailer):
    await _register_and_verify(client, mailer)
    login = await _login(client, REGISTER["email"], REGISTER["password"])
    refresh_token = login.json()["refresh_token"]

    await client.post("/auth/forgot-password", json={"email": REGISTER["email"]})
    token = mailer.last_token()
    await client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "brandnew-pass-9"},
    )

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


# --- Refresh / logout (Story 4) --------------------------------------------


@pytest.mark.asyncio
async def test_login_blocked_until_email_verified(client, mailer):
    await _register(client, mailer)
    resp = await _login(client, REGISTER["email"], REGISTER["password"])
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "email_not_verified"

    # After verifying, the same credentials sign in.
    await client.post("/auth/verify-email", json={"token": mailer.last_token()})
    assert (await _login(client, REGISTER["email"], REGISTER["password"])).status_code == 200


@pytest.mark.asyncio
async def test_login_returns_access_and_refresh(client, mailer):
    await _register_and_verify(client, mailer)
    body = (await _login(client, REGISTER["email"], REGISTER["password"])).json()
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_rotates_and_rejects_reused_token(client, mailer):
    await _register_and_verify(client, mailer)
    login = await _login(client, REGISTER["email"], REGISTER["password"])
    old_refresh = login.json()["refresh_token"]

    rotated = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    # New access token works.
    me = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {rotated.json()['access_token']}"},
    )
    assert me.status_code == 200

    # Reusing the rotated (old) token is rejected.
    reuse = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401

    # Reuse detection invalidated the family: the new token is dead too.
    after = await client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(client, mailer):
    resp = await client.post("/auth/refresh", json={"refresh_token": "not-a-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, mailer):
    await _register_and_verify(client, mailer)
    login = await _login(client, REGISTER["email"], REGISTER["password"])
    refresh_token = login.json()["refresh_token"]

    logout = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


# --- Rate limiting (Story 5) -----------------------------------------------


@pytest.mark.asyncio
async def test_login_is_rate_limited_after_threshold(client, mailer):
    await _register(client, mailer)
    for _ in range(5):
        resp = await _login(client, REGISTER["email"], "wrong-password")
        assert resp.status_code == 401

    limited = await _login(client, REGISTER["email"], "wrong-password")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert "retry-after" in {k.lower() for k in limited.headers}


@pytest.mark.asyncio
async def test_successful_login_resets_failure_counter(client, mailer):
    await _register_and_verify(client, mailer)
    for _ in range(4):
        assert (await _login(client, REGISTER["email"], "wrong-password")).status_code == 401

    ok = await _login(client, REGISTER["email"], REGISTER["password"])
    assert ok.status_code == 200

    # Counter cleared: a further wrong attempt is 401 (not immediately 429).
    again = await _login(client, REGISTER["email"], "wrong-password")
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_is_rate_limited(client, mailer):
    # Same IP hammering forgot-password gets throttled after the threshold.
    for _ in range(5):
        resp = await client.post(
            "/auth/forgot-password", json={"email": "ghost@example.com"}
        )
        assert resp.status_code == 200
    limited = await client.post(
        "/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert limited.status_code == 429
