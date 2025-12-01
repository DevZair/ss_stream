from __future__ import annotations

from typing import Set


def accessible_sections(request) -> dict[str, set[str]]:
    """Expose allowed section slugs for sidebar/toolbar visibility."""
    slugs: Set[str] = set()
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if user.is_superuser:
            slugs = {
                "categories",
                "products",
                "warehouses",
                "employees",
                "stocks",
                "operations",
                "reports",
                "incoming",
                "movements",
                "sales",
            }
        else:
            employee = getattr(user, "employee_profile", None)
            if employee:
                slugs = set(employee.access_sections.values_list("slug", flat=True))
    return {"accessible_sections": slugs}
