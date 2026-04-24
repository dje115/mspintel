import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.core.settings import get_settings
from app.models.entities import (
    AIProvider,
    OnboardingState,
    Plan,
    Role,
    Subscription,
    Tenant,
    TenantMembership,
    User,
)


ROLE_SEED = {
    "platform_admin": "Cross-tenant platform operator",
    "tenant_admin": "Tenant-level admin",
    "director": "Tenant executive viewer",
    "sales_user": "Sales user",
    "account_manager": "Account manager",
    "service_manager": "Service manager",
    "marketing_user": "Marketing user",
}


def seed_all(db: Session) -> None:
    settings = get_settings()

    existing_roles = {r.code for r in db.scalars(select(Role)).all()}
    for code, desc in ROLE_SEED.items():
        if code not in existing_roles:
            db.add(Role(id=uuid.uuid4(), code=code, description=desc))

    plans = {p.code: p for p in db.scalars(select(Plan)).all()}
    if "starter" not in plans:
        db.add(Plan(id=uuid.uuid4(), code="starter", name="Starter", price_monthly_cents=9900, is_active=True))
    if "growth" not in plans:
        db.add(Plan(id=uuid.uuid4(), code="growth", name="Growth", price_monthly_cents=24900, is_active=True))

    db.commit()

    platform_admin = db.scalars(select(User).where(User.email == settings.seed_platform_admin_email)).first()
    if not platform_admin:
        platform_admin = User(
            id=uuid.uuid4(),
            email=settings.seed_platform_admin_email,
            full_name="Platform Admin",
            password_hash=get_password_hash(settings.seed_platform_admin_password),
            is_platform_admin=True,
        )
        db.add(platform_admin)

    tenant = db.scalars(select(Tenant).where(Tenant.slug == "demo-msp")).first()
    if not tenant:
        tenant = Tenant(id=uuid.uuid4(), slug="demo-msp", name="Demo MSP")
        db.add(tenant)

    db.commit()

    roles = {r.code: r for r in db.scalars(select(Role)).all()}
    users_data = [
        ("tenant-admin@demo-msp.example.com", "Tenant Admin", "tenant_admin"),
        ("sales@demo-msp.example.com", "Sales User", "sales_user"),
        ("service@demo-msp.example.com", "Service Manager", "service_manager"),
    ]
    users = {}
    for email, name, role_code in users_data:
        user = db.scalars(select(User).where(User.email == email)).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                full_name=name,
                password_hash=get_password_hash("ChangeMe123!"),
                is_platform_admin=False,
            )
            db.add(user)
            db.flush()
        users[email] = (user, role_code)

    db.commit()

    for _, (user, role_code) in users.items():
        membership = db.scalars(
            select(TenantMembership).where(TenantMembership.user_id == user.id, TenantMembership.tenant_id == tenant.id)
        ).first()
        if not membership:
            db.add(
                TenantMembership(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role_id=roles[role_code].id,
                    status="active",
                )
            )

    onboarding = db.scalars(select(OnboardingState).where(OnboardingState.tenant_id == tenant.id)).first()
    if not onboarding:
        db.add(OnboardingState(id=uuid.uuid4(), tenant_id=tenant.id, status="in_progress", step="connect_systems"))

    starter_plan = db.scalars(select(Plan).where(Plan.code == "starter")).first()
    subscription = db.scalars(select(Subscription).where(Subscription.tenant_id == tenant.id)).first()
    if not subscription and starter_plan:
        db.add(Subscription(id=uuid.uuid4(), tenant_id=tenant.id, plan_id=starter_plan.id, status="trial"))

    from app.services.demo_rich_seed import seed_demo_workspace_if_demo_tenant

    seed_demo_workspace_if_demo_tenant(db, tenant)

    if not db.scalars(select(AIProvider).where(AIProvider.tenant_id == tenant.id)).first():
        db.add(
            AIProvider(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                provider_name="openai",
                status="configured",
                catalog_code="openai_hosted",
                provider_family="openai",
                deployment_mode="hosted",
                display_label="OpenAI (demo)",
                is_enabled=True,
            )
        )
        db.flush()

    from app.services.ai_foundation_seed import (
        ensure_ai_provider_catalog,
        ensure_demo_tenant_ai_provider,
        ensure_legacy_prompt_aliases,
        ensure_platform_default_prompts,
    )

    ensure_ai_provider_catalog(db)
    ensure_platform_default_prompts(db)
    ensure_legacy_prompt_aliases(db)
    if tenant:
        ensure_demo_tenant_ai_provider(db, tenant.id)

    db.commit()
