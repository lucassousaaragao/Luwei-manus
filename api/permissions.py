from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db_models import WorkspaceMember, OrganizationMember, UserRole


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


async def verify_org_access(
    db: AsyncSession,
    org_id: str,
    user_id: int
) -> bool:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None