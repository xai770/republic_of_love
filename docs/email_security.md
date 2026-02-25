# Email Security at talent.yoga

**Last updated:** 2026-02-25
**Status:** Implemented (commit `9680286`)

---

## Core Principle

> We never assume we have an email from a user. We never store one unencrypted. We never expose a plaintext email address to a route handler, template, or API response.

Most talent.yoga users are anonymous by design. An email address is an opt-in, explicitly consented extra — not a baseline assumption.

---

## What We Store

| Field | Table | Always encrypted? | Notes |
|---|---|---|---|
| `email` | `users` | ✅ Yes (Fernet) | Google login email, stored at account creation |
| `notification_email` | `users` | ✅ Yes (Fernet) | User-provided, optional, explicit consent required |

Both fields use Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) via `lib/crypto.py`. The key lives in `EMAIL_ENCRYPTION_KEY` in `.env`. A stolen DB dump without the key is useless.

---

## What We Do NOT Do

- ❌ Fall back to the Google login email when a notification address isn't provided
- ❌ Decrypt email in `get_current_user()` / `deps.py` (would spread plaintext to every route)
- ❌ Return plaintext email in any API response
- ❌ Show plaintext email in any template (header, account page, admin views)
- ❌ Use `user.email` as a display name fallback anywhere in the UI

---

## Encryption / Decryption Flow

```
Google OAuth
    │
    ▼
auth.py: encrypt_email(google_email) → store ciphertext in users.email
    │
    └─ Never decrypted again unless explicitly needed (see below)

User opts into notifications (onboarding step 11 or Settings)
    │
    ▼
account.py /email-consent: encrypt_email(data.email) → store in users.notification_email
    │
    └─ data.email must be explicitly provided — no fallback to login email
```

### Authorised decrypt call sites

Only three places in the codebase are permitted to call `decrypt_email()`:

| Location | Purpose |
|---|---|
| `api/main.py` → `/settings` route | Decrypt → mask → pass `masked_notification_email` to template |
| `api/routers/notifications.py` → `GET /consent` | Decrypt → mask → return in API response |
| `api/routers/notifications.py` → `PUT /consent` | Decrypt → mask → echo back in API response |

Any future call site must have a documented reason. The notification worker (not yet built) will be the fourth permitted site.

---

## Masking

`lib/crypto.py` provides `mask_email(plaintext)` → e.g. `ma***@gmail.com`.

Rules:
- Always call `decrypt_email()` first — never pass ciphertext to `mask_email()`
- Returns `None` if the value is `None`, empty, or lacks an `@`
- First 2 characters of the local part are visible; everything up to `@` is replaced by `***`

This is the only form in which an email address ever reaches the browser or a template variable.

---

## What This Does and Doesn't Protect Against

| Threat | Protected? |
|---|---|
| Stolen DB dump | ✅ Ciphertext is useless without the key |
| Rogue DB admin with DB-only access | ✅ Same — only ciphertext visible |
| Compromised server with `.env` access | ❌ Key + ciphertext = plaintext (unavoidable for a sending service) |
| Law enforcement subpoena | ❌ We hold the key and can comply |
| talent.yoga staff curiosity | ✅ No UI or API path returns plaintext; decryption requires a code change + audit trail |

This is **Option 2** from the hardening discussion: structurally narrow the decrypt path so that reading emails requires deliberate engineering effort, not just a DB query.

---

## Key Management

- Key is a 32-byte base64url Fernet key: `Fernet.generate_key()`
- Stored in `.env` as `EMAIL_ENCRYPTION_KEY`
- **Back it up like a password.** Key loss = permanent loss of all stored email addresses.
- The app will refuse to start in production if the key is not set (`api/config.py` enforces this).
- `lib/crypto.py` is force-tracked in git (`git add -f`) despite `lib/` being in `.gitignore` — this is intentional.

---

## Relevant Files

- [lib/crypto.py](../lib/crypto.py) — `encrypt_email`, `decrypt_email`, `mask_email`, `is_encrypted`
- [api/deps.py](../api/deps.py) — `get_current_user` (does NOT decrypt)
- [api/routers/account.py](../api/routers/account.py) — consent write path
- [api/routers/notifications.py](../api/routers/notifications.py) — consent read/update API
- [api/main.py](../api/main.py) — `/settings` page render
- [frontend/templates/account.html](../frontend/templates/account.html) — uses `masked_notification_email`
- [frontend/templates/partials/header.html](../frontend/templates/partials/header.html) — no email fallback
