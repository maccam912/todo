"""Core application modules."""
from app.core.auth import (
    authenticate_user,
    create_api_token,
    create_scope,
    create_session_token,
    create_user,
    get_user_by_id,
    update_password,
    verify_api_token,
    verify_session_token,
)
from app.core.scope import (
    Scope,
    can_access_task,
    can_modify_group,
    can_modify_task,
    check_circular_group_reference,
    get_tasks_for_scope,
    get_user_group_ids,
)
from app.core.security import (
    generate_access_token,
    generate_random_token,
    generate_session_token,
    hash_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    # Auth
    "authenticate_user",
    "create_user",
    "create_session_token",
    "verify_session_token",
    "create_api_token",
    "verify_api_token",
    "get_user_by_id",
    "create_scope",
    "update_password",
    # Scope
    "Scope",
    "get_user_group_ids",
    "check_circular_group_reference",
    "get_tasks_for_scope",
    "can_access_task",
    "can_modify_task",
    "can_modify_group",
    # Security
    "hash_password",
    "verify_password",
    "generate_random_token",
    "generate_access_token",
    "generate_session_token",
    "hash_access_token",
]
