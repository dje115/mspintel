"""Tenant membership role and status rules.

These rules are enforced server-side by MembershipService and documented here:

- Assignable roles: the same set used for invitations (no platform_admin via tenant UI).
- Membership status: ``active`` (can access tenant) or ``suspended`` (blocked from AccessContext).
- At least one ``active`` member with role ``tenant_admin`` must remain per tenant at all times.
- Actors with ``membership:write`` (tenant admin or platform-equivalent) may update other members
  in the same tenant only; cross-tenant updates are rejected by scoping queries.
- Self-service: a member may not apply a change that would remove the last active tenant admin
  (including demoting or suspending themselves when they are the sole admin).
- Role codes in API payloads are normalized to lowercase stripped strings before validation.
"""

from __future__ import annotations

# Tenant-scoped roles that may assign the ``tenant_admin`` role to another member (plus
# ``is_platform_admin`` on the user account, which bypasses tenant role checks elsewhere).
ROLES_THAT_MAY_ASSIGN_TENANT_ADMIN: frozenset[str] = frozenset({"tenant_admin", "platform_admin"})

ASSIGNABLE_TENANT_ROLE_CODES: frozenset[str] = frozenset(
    {
        "tenant_admin",
        "director",
        "sales_user",
        "account_manager",
        "service_manager",
        "marketing_user",
    }
)

MEMBERSHIP_STATUSES: frozenset[str] = frozenset({"active", "suspended"})
