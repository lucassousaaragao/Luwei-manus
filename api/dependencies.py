from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database_async import get_db
from api.auth import get_current_user
from api.db_models import UserRole, WorkspaceMember, OrganizationMember

security = HTTPBearer()


async def verify_workspace_access(
    db: AsyncSession,
    workspace_id: str,
    user_id: int,
    allowed_roles: Optional[List[UserRole]] = None
) -> bool:
    if allowed_roles is None:
        allowed_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER]
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.role.in_(allowed_roles),
        )
    )
    return result.scalar_one_or_none() is not None


async def require_workspace_access(
    workspace_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    allowed_roles: Optional[List[UserRole]] = None
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"], allowed_roles)
    if not has_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to workspace")
    return True


async def verify_org_access(db: AsyncSession, org_id: str, user_id: int) -> bool:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def require_org_access(
    org_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_org_access(db, org_id, user["id"])
    if not has_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to organization")
    return True