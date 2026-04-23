from datetime import UTC, datetime, timedelta
import uuid

from app.models.entities import Tenant, TenantInvitation, User
from app.repositories.invitations import InvitationRepository
from app.services.invitation_sweep import sweep_expired_invitations


def test_expire_pending_past_expiry_marks_rows(db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="sw", name="Sweep", is_active=True)
    user = User(
        id=uuid.uuid4(),
        email="inviter@example.com",
        full_name="Inviter",
        password_hash="x",
        is_platform_admin=False,
    )
    db_session.add_all([tenant, user])
    db_session.commit()

    past = datetime.now(UTC) - timedelta(days=1)
    future = datetime.now(UTC) + timedelta(days=1)

    old = TenantInvitation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="old@example.com",
        role_to_assign="sales_user",
        invited_by_user_id=user.id,
        token="tok-old-" + uuid.uuid4().hex,
        status="pending",
        expires_at=past,
    )
    still = TenantInvitation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="still@example.com",
        role_to_assign="sales_user",
        invited_by_user_id=user.id,
        token="tok-new-" + uuid.uuid4().hex,
        status="pending",
        expires_at=future,
    )
    db_session.add_all([old, still])
    db_session.commit()

    n = InvitationRepository(db_session).expire_pending_past_expiry()
    assert n == 1

    db_session.refresh(old)
    db_session.refresh(still)
    assert old.status == "expired"
    assert still.status == "pending"

    assert sweep_expired_invitations(db_session) == 0
