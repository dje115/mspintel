from datetime import UTC, datetime
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    AUTH_MODE_TENANT,
    create_access_token,
    create_refresh_token,
    auth_mode_from_refresh_payload,
    decode_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.models.entities import OnboardingState, Plan, Role, Subscription, Tenant, TenantMembership, User, UserSession
from app.repositories.sessions import SessionRepository
from app.schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenPairResponse
from app.services.audit import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.sessions = SessionRepository(db)
        self.audit = AuditService(db)

    def authenticate(self, payload: LoginRequest) -> User | None:
        user = self.db.scalars(select(User).where(User.email == payload.email.lower())).first()
        if not user or not verify_password(payload.password, user.password_hash):
            return None
        return user

    def signup(self, payload: SignupRequest) -> User:
        existing = self.db.scalars(select(User).where(User.email == payload.email.lower())).first()
        if existing:
            raise ValueError("User already exists")

        tenant_slug = payload.tenant_name.strip().lower().replace(" ", "-")[:60]
        tenant = Tenant(id=uuid.uuid4(), name=payload.tenant_name.strip(), slug=tenant_slug)
        user = User(
            id=uuid.uuid4(),
            email=payload.email.lower(),
            full_name=payload.full_name.strip(),
            password_hash=get_password_hash(payload.password),
            is_platform_admin=False,
        )
        self.db.add_all([tenant, user])
        self.db.flush()

        tenant_admin_role = self.db.scalars(select(Role).where(Role.code == "tenant_admin")).first()
        if not tenant_admin_role:
            raise ValueError("Role seed missing")

        membership = TenantMembership(
            id=uuid.uuid4(), tenant_id=tenant.id, user_id=user.id, role_id=tenant_admin_role.id, status="active"
        )

        trial_plan = self.db.scalars(select(Plan).where(Plan.code == "starter")).first()
        if not trial_plan:
            raise ValueError("Plan seed missing")

        subscription = Subscription(id=uuid.uuid4(), tenant_id=tenant.id, plan_id=trial_plan.id, status="trial")
        onboarding = OnboardingState(id=uuid.uuid4(), tenant_id=tenant.id, status="in_progress", step="welcome")

        self.db.add_all([membership, subscription, onboarding])
        self.db.commit()
        self.db.refresh(user)
        return user

    def issue_token_pair(
        self,
        user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
        auth_mode: str = AUTH_MODE_TENANT,
    ) -> TokenPairResponse:
        session_id = uuid.uuid4()
        access_token = create_access_token(str(user.id), session_id=session_id, auth_mode=auth_mode)
        refresh_token = create_refresh_token(str(user.id), auth_mode=auth_mode)

        decoded = decode_token(refresh_token)
        if not decoded or "exp" not in decoded:
            raise ValueError("Unable to create refresh session")
        expires_at = datetime.fromtimestamp(int(decoded["exp"]), tz=UTC)

        self.sessions.create(
            UserSession(
                id=session_id,
                user_id=user.id,
                refresh_token_hash=hash_refresh_token(refresh_token),
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                device_label=device_label,
                last_used_at=datetime.now(UTC),
            )
        )
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=session_id,
        )

    def refresh(
        self,
        payload: RefreshRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> TokenPairResponse:
        decoded = decode_token(payload.refresh_token)
        if not decoded or decoded.get("typ") != "refresh" or not decoded.get("sub"):
            raise ValueError("Invalid refresh token")

        session = self.sessions.by_refresh_hash(hash_refresh_token(payload.refresh_token))
        if not session:
            raise ValueError("Session not found")
        if not self.sessions.is_active(session):
            self.sessions.revoke(session)
            raise ValueError("Session expired or revoked")

        user = self.db.get(User, session.user_id)
        if not user or str(user.id) != str(decoded["sub"]):
            raise ValueError("User not found")

        auth_mode = auth_mode_from_refresh_payload(decoded)

        self.sessions.touch(session)
        self.sessions.revoke(session)
        return self.issue_token_pair(
            user,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device_label,
            auth_mode=auth_mode,
        )

    def logout(self, refresh_token: str) -> None:
        session = self.sessions.by_refresh_hash(hash_refresh_token(refresh_token))
        if session and self.sessions.is_active(session):
            self.sessions.revoke(session)

    def logout_all(self, user_id: UUID, *, keep_refresh_token: str | None = None) -> int:
        if keep_refresh_token:
            keep_hash = hash_refresh_token(keep_refresh_token)
            session = self.sessions.by_refresh_hash(keep_hash)
            if not session or session.user_id != user_id:
                raise ValueError("keep_refresh_token does not match an active session for this user")
            if not self.sessions.is_active(session):
                raise ValueError("keep_refresh_token session is not active")
            return self.sessions.revoke_all_for_user_except_refresh_hash(user_id, keep_hash)
        return self.sessions.revoke_all_for_user(user_id)

    def revoke_session_for_user(
        self,
        user_id: UUID,
        session_id: UUID,
        *,
        tenant_id_for_audit: UUID | None,
        actor_user_id: UUID,
    ) -> bool:
        """Revoke a session owned by ``user_id``. Returns True if revoked, False if already inactive."""
        session = self.sessions.get_for_user(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        if session.revoked_at is not None or not self.sessions.is_active(session):
            return False
        session.revoked_at = datetime.now(UTC)
        if tenant_id_for_audit is not None:
            self.audit.log(
                tenant_id=tenant_id_for_audit,
                actor_user_id=actor_user_id,
                event_type="session.revoked",
                details={"session_id": str(session_id), "target_user_id": str(user_id)},
            )
        self.db.commit()
        return True
