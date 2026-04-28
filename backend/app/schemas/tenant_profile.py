from uuid import UUID

from pydantic import BaseModel, Field


DEFAULT_SERVICE_CATALOG: list[tuple[str, str]] = [
    ("managed_support", "Managed support"),
    ("m365_management", "Microsoft 365 management"),
    ("backup_disaster_recovery", "Backup / disaster recovery"),
    ("security", "Security"),
    ("network", "Network"),
    ("cloud", "Cloud"),
    ("identity_mfa_conditional_access", "Identity / MFA / conditional access"),
    ("endpoint_management", "Endpoint management"),
    ("compliance", "Compliance"),
    ("projects_migrations", "Projects / migrations"),
    ("vcio_qbr", "vCIO / QBR"),
    ("telephony", "Telephony"),
    ("procurement_licensing_resale", "Procurement / licensing resale"),
]


class TenantMspProfilePayload(BaseModel):
    legal_name: str | None = None
    brand_name: str | None = None
    regions_served: list[str] = Field(default_factory=list)
    vertical_focus: list[str] = Field(default_factory=list)
    team_size_band: str | None = None
    customer_count_band: str | None = None
    typical_customer_size_band: str | None = None
    delivery_model: str | None = None
    business_goals: list[str] = Field(default_factory=list)
    free_text_description: str | None = None


class TenantMspProfileResponse(TenantMspProfilePayload):
    tenant_id: UUID


class TenantServiceCatalogEntryPayload(BaseModel):
    service_key: str
    service_name: str
    is_selected: bool = True
    is_custom: bool = False
    sort_order: int = 0


class TenantServiceCatalogResponse(BaseModel):
    tenant_id: UUID
    items: list[TenantServiceCatalogEntryPayload] = Field(default_factory=list)


class TenantAIContextResponse(BaseModel):
    tenant_id: UUID
    msp_profile_summary: dict
    selected_services: list[str] = Field(default_factory=list)
    business_goals: list[str] = Field(default_factory=list)
    vertical_focus: list[str] = Field(default_factory=list)
    regions_served: list[str] = Field(default_factory=list)
    data_confidence_notes: list[str] = Field(default_factory=list)

