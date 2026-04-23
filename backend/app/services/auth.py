from datetime import UTC, datetime
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.models.entities import OnboardingState, Plan, Role, Subscription, Tenant, TenantMembership, User, UserSession
from app.repositories.sessions import SessionRepository
from app.schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenPairResponse

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.sessions = SessionRepository(db)

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

    def issue_token_pair(self, user: User) -> TokenPairResponse:
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        decoded = decode_token(refresh_token)
        if not decoded or "exp" not in decoded:
            raise ValueError("Unable to create refresh session")
        expires_at = datetime.fromtimestamp(int(decoded["exp"]), tz=UTC)

        self.sessions.create(
            UserSession(
                id=uuid.uuid4(),
                user_id=user.id,
                refresh_token_hash=hash_refresh_token(refresh_token),
                expires_at=expires_at,
            )
        )
        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)

    def refresh(self, payload: RefreshRequest) -> TokenPairResponse:
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

        self.sessions.revoke(session)
        return self.issue_token_pair(user)

    def logout(self, refresh_token: str) -> None:
        session = self.sessions.by_refresh_hash(hash_refresh_token(refresh_token))
        if session and self.sessions.is_active(session):
            self.sessions.revoke(session)

    def logout_all(self, user_id: UUID) -> int:
        return self.sessions.revoke_all_for_user(user_id)
