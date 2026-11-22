"""Fail-closed authorization helpers for service-layer project operations.

Call these helpers at the service boundary, after resolving the resource's
canonical project_id from the database (never from an untrusted request body).
"""
from __future__ import annotations

from typing import Any

from services.access_control import AccessControl, AccessDenied


class ProjectAuthorization:
    """Bind a verified principal to an AccessControl policy.

    The principal must come from AccessControl.verify_session(), not a UI form,
    request header, or caller-supplied role. Missing identity fails closed.
    """

    def __init__(self, access_control: AccessControl) -> None:
        if not isinstance(access_control, AccessControl):
            raise TypeError("access_control must be an AccessControl instance")
        self.access_control = access_control

    @staticmethod
    def require_principal(principal: Any) -> dict[str, Any]:
        if not isinstance(principal, dict):
            raise AccessDenied("Authenticated principal is required")
        user_id = principal.get("id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise AccessDenied("Authenticated principal is required")
        return principal

    def require_read(self, principal: Any, project_id: str) -> None:
        self.access_control.require_project(
            self.require_principal(principal), project_id, permission="read"
        )

    def require_write(self, principal: Any, project_id: str) -> None:
        self.access_control.require_project(
            self.require_principal(principal), project_id, permission="write"
        )

    def require_manage(self, principal: Any, project_id: str) -> None:
        self.access_control.require_project(
            self.require_principal(principal), project_id, permission="manage"
        )

    def require_resource_read(self, principal: Any, resource: Any) -> str:
        project_id = self._resource_project_id(resource)
        self.require_read(principal, project_id)
        return project_id

    def require_resource_write(self, principal: Any, resource: Any) -> str:
        project_id = self._resource_project_id(resource)
        self.require_write(principal, project_id)
        return project_id

    @staticmethod
    def _resource_project_id(resource: Any) -> str:
        if not isinstance(resource, dict):
            raise AccessDenied("Resource not found")
        project_id = resource.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            # Do not reveal whether an inaccessible resource exists.
            raise AccessDenied("Resource not found")
        return project_id
