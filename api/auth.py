import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from api.database_async import get_db, AsyncSession
from api.db_models import User, OrganizationMember, WorkspaceMember, UserRole, Organization, Workspace

router = APIRouter(prefix="/api/auth")
security = HTTPBearer()
JWT_SECRET = os.environ.get("JWT_SECRET", "luwei-secret-change-in-production")


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class OrgCreateRequest(BaseModel):
    name: str
    slug: str
    description: str = ""


def create_token(user_id: int, email: str, org_id: Optional[str] = None) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "org_id": org_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    return {
        "id": int(payload["sub"]),
        "email": payload["email"],
        "org_id": payload.get("org_id"),
    }


async def get_user_orgs(db: AsyncSession, user_id: int) -> List[dict]:
    """Get user's organizations with roles."""
    result = await db.execute(
        select(OrganizationMember, Organization)
        .join(Organization)
        .where(OrganizationMember.user_id == user_id)
    )
    orgs = []
    for om, org in result:
        orgs.append({
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "role": om.role.value,
        })
    return orgs


async def get_user_workspaces(db: AsyncSession, user_id: int, org_id: Optional[str] = None) -> List[dict]:
    """Get user's workspaces, optionally filtered by org."""
    query = (
        select(WorkspaceMember, Workspace)
        .join(Workspace)
        .where(WorkspaceMember.user_id == user_id)
    )
    if org_id:
        query = query.where(Workspace.organization_id == org_id)
    result = await db.execute(query)
    workspaces = []
    for wm, ws in result:
        workspaces.append({
            "id": ws.id,
            "name": ws.name,
            "organization_id": ws.organization_id,
            "role": wm.role.value,
        })
    return workspaces


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload["sub"])
        email = payload["email"]
        token_org_id = payload.get("org_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    # Get user's orgs
    orgs = await get_user_orgs(db, user_id)
    if not orgs:
        raise HTTPException(403, "User not member of any organization")

    # Determine active org: from token, or first org
    active_org = None
    if token_org_id:
        active_org = next((o for o in orgs if o["id"] == token_org_id), None)
    if not active_org:
        active_org = orgs[0]

    # Get workspaces for active org
    workspaces = await get_user_workspaces(db, user_id, active_org["id"])

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "org_id": active_org["id"],
        "org_name": active_org["name"],
        "org_slug": active_org["slug"],
        "org_role": active_org["role"],
        "orgs": orgs,
        "workspaces": workspaces,
        "workspace_ids": [w["id"] for w in workspaces],
    }


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=req.email, password_hash=pw_hash, name=req.name)
    db.add(user)
    await db.flush()  # Get user.id

    # Create default organization for the user
    org_slug = req.email.split("@")[0].lower().replace(".", "-")[:50]
    org = Organization(name=f"{req.name or 'User'}'s Organization", slug=org_slug, description="Default organization")
    db.add(org)
    await db.flush()

    # Add user as owner
    om = OrganizationMember(organization_id=org.id, user_id=user.id, role=UserRole.OWNER)
    db.add(om)

    # Create default workspace
    ws = Workspace(organization_id=org.id, name="Workspace Principal", description="Workspace principal", created_by=user.id)
    db.add(ws)
    await db.flush()

    # Add user as owner of workspace
    wm = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.OWNER)
    db.add(wm)

    await db.commit()

    token = create_token(user.id, user.email, org.id)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "Invalid email or password")
    if not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")

    orgs = await get_user_orgs(db, user.id)
    if not orgs:
        raise HTTPException(403, "User not member of any organization")

    active_org = orgs[0]
    workspaces = await get_user_workspaces(db, user.id, active_org["id"])

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_token(user.id, user.email, active_org["id"])
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "org_id": active_org["id"],
            "org_name": active_org["name"],
            "org_slug": active_org["slug"],
            "org_role": active_org["role"],
            "orgs": orgs,
            "workspaces": workspaces,
            "workspace_ids": [w["id"] for w in workspaces],
        },
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/organizations")
async def create_organization(req: OrgCreateRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check if user can create org (simplified: any authenticated user)
    existing = await db.execute(select(Organization).where(Organization.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Slug already taken")

    org = Organization(name=req.name, slug=req.slug, description=req.description)
    db.add(org)
    await db.flush()

    om = OrganizationMember(organization_id=org.id, user_id=user["id"], role=UserRole.OWNER, invited_by=user["id"])
    db.add(om)

    ws = Workspace(organization_id=org.id, name="Workspace Principal", created_by=user["id"])
    db.add(ws)
    await db.flush()

    wm = WorkspaceMember(workspace_id=ws.id, user_id=user["id"], role=UserRole.OWNER)
    db.add(wm)

    await db.commit()

    return {"id": org.id, "name": org.name, "slug": org.slug, "description": org.description}


@router.get("/organizations")
async def list_organizations(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return user["orgs"]


@router.post("/switch-organization/{org_id}")
async def switch_organization(org_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Verify user is member of this org
    org = next((o for o in user["orgs"] if o["id"] == org_id), None)
    if not org:
        raise HTTPException(403, "Not a member of this organization")

    workspaces = await get_user_workspaces(db, user["id"], org_id)

    # Create new token with new org_id
    token = create_token(user["id"], user["email"], org_id)

    return {
        "token": token,
        "user": {
            **user,
            "org_id": org["id"],
            "org_name": org["name"],
            "org_slug": org["slug"],
            "org_role": org["role"],
            "workspaces": workspaces,
            "workspace_ids": [w["id"] for w in workspaces],
        },
    }