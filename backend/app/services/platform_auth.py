"""Platform-operator authentication extension points.

Tenant sign-in remains in :mod:`app.api.v1.auth` ``login``. Platform sign-in is isolated in
``platform_login`` and should call :func:`validate_platform_login_extras` **before** tokens
are minted.

Future hardening (MFA, WebAuthn, step-up, geo rules) should:
- validate secondary factors here (or delegate to a dedicated verifier service)
- raise ``ValueError`` with a **safe, non-enumerating** user message on failure
- keep HTTP mapping in the router (typically 401 with a generic body)

Do **not** reuse tenant MFA hooks here without an explicit product decision: platform sessions
use a different JWT scope (``am=platform``) and often warrant stricter controls.
"""

from app.models.entities import User


def validate_platform_login_extras(user: User, *, ip: str | None, user_agent: str | None) -> None:
    """Hook invoked after password check and before session/token issuance.

    Reserved for MFA / step-up / device trust. Default: no-op.
    """
    del user, ip, user_agent
