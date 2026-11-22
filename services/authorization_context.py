"""Optional, verified-principal authorization context for service boundaries."""
from __future__ import annotations
from functools import wraps
from inspect import signature
from typing import Any, Callable
from services.access_control import AccessDenied
from services.authorization import ProjectAuthorization

class AuthorizationContext:
    """Request-scoped policy and principal. Construct only from verify_session()."""
    def __init__(self, policy: ProjectAuthorization, principal: dict[str, Any]):
        self.policy = policy
        self.principal = policy.require_principal(principal)

    def require(self, project_id: str, permission: str = "read") -> None:
        if permission == "read": self.policy.require_read(self.principal, project_id)
        elif permission == "write": self.policy.require_write(self.principal, project_id)
        elif permission == "manage": self.policy.require_manage(self.principal, project_id)
        else: raise ValueError("Unsupported permission")

    def require_admin(self) -> None:
        # The principal is revalidated against the live account row by AccessControl.
        if self.principal.get("role") != "admin":
            raise AccessDenied("Administrator access required")
        with self.policy.access_control.database.connection() as c:
            row=c.execute("SELECT enabled,role FROM pc_users WHERE id=?",(self.principal["id"],)).fetchone()
        if row is None or not row["enabled"] or row["role"] != "admin":
            raise AccessDenied("Administrator access required")

def requires_project(permission: str, *, project_arg: str | None = None,
                     resource_arg: str | None = None, resolver: str | None = None):
    """Guard a service call using canonical DB resource scope, never caller scope."""
    def decorate(fn: Callable):
        sig=signature(fn)
        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            ctx=getattr(self,"authorization_context",None)
            if ctx is not None:
                bound=sig.bind(self,*args,**kwargs)
                if project_arg:
                    project_id=bound.arguments.get(project_arg)
                elif resource_arg:
                    key=bound.arguments.get(resource_arg)
                    lookup=getattr(self,resolver) if resolver else getattr(self.repository,resolver or "")
                    resource=lookup(key)
                    if resource is None: raise AccessDenied("Resource not found")
                    project_id=resource.get("project_id")
                else:
                    raise RuntimeError("Authorization guard has no resource scope")
                if not isinstance(project_id,str) or not project_id:
                    raise AccessDenied("Resource not found")
                ctx.require(project_id,permission)
            return fn(self,*args,**kwargs)
        return wrapped
    return decorate
