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
    TenantAiSettings,
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
        provider_family = (settings.ai_default_provider or "ollama").strip().lower()
        deployment_mode = (settings.ai_default_mode or "local").strip().lower()
        default_model = (
            settings.ollama_default_model
            if provider_family == "ollama"
            else (settings.ai_default_model or "llama3.2:3b")
        )
        base_url = settings.ollama_base_url if provider_family == "ollama" else None
        catalog_by_family = {
            "openai": "openai_hosted",
            "azure_openai": "azure_openai_hosted",
            "anthropic": "anthropic_hosted",
            "google": "google_hosted",
            "microsoft_copilot": "microsoft_copilot_microsoft",
            "openrouter": "openrouter_hosted",
            "ollama": "ollama_local",
            "vllm": "vllm_self",
            "lm_studio": "lm_studio_local",
            "openai_compatible": "openai_compatible_self",
        }
        db.add(
            AIProvider(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                provider_name=provider_family[:60],
                status="configured",
                catalog_code=catalog_by_family.get(provider_family),
                provider_family=provider_family,
                deployment_mode=deployment_mode,
                display_label=f"{provider_family.replace('_', ' ').title()} (demo)",
                base_url=base_url,
                is_enabled=True,
            )
        )
        db.flush()
        provider_row = db.scalars(select(AIProvider).where(AIProvider.tenant_id == tenant.id)).first()
        if provider_row and not db.scalars(select(TenantAiSettings).where(TenantAiSettings.tenant_id == tenant.id)).first():
            db.add(
                TenantAiSettings(
                    tenant_id=tenant.id,
                    default_ai_provider_id=provider_row.id,
                    default_model=default_model,
                    fallback_ai_provider_id=None,
                    fallback_model=None,
                    extra={"seeded_via_env": True},
                    updated_by_user_id=None,
                )
            )

    from app.services.ai_foundation_seed import (
        ensure_ai_provider_catalog,
        ensure_demo_tenant_ai_provider,
        ensure_legacy_prompt_aliases,
        sync_platform_prompt_catalog,
    )

    ensure_ai_provider_catalog(db)
    sync_platform_prompt_catalog(db)
    ensure_legacy_prompt_aliases(db)
    if tenant:
        ensure_demo_tenant_ai_provider(db, tenant.id)

    db.commit()
