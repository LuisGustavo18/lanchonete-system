ROLE_PERMISSIONS = {
    "OWNER": {
        "manage_comandas",
        "manage_products",
        "manage_service_charge",
        "process_payment",
        "manage_users",
    },
    "MANAGER": {
        "manage_comandas",
        "manage_products",
        "manage_service_charge",
        "process_payment",
    },
    "STAFF": {
        "manage_comandas",
        "process_payment",
    },
}


def has_permission(membership, permission):
    return permission in ROLE_PERMISSIONS.get(
        membership.role,
        set()
    )