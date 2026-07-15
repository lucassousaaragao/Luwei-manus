from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, DateTime, ForeignKey, Integer, Boolean, Enum as SQLEnum,
    Index, UniqueConstraint, func, select
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base

Base = declarative_base()


class UserRole(PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    members: Mapped[List["OrganizationMember"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    workspaces: Mapped[List["Workspace"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("ix_org_member_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False)
    invited_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    inviter: Mapped[Optional["User"]] = relationship(foreign_keys=[invited_by])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org_memberships: Mapped[List["OrganizationMember"]] = relationship(back_populates="user", foreign_keys="OrganizationMember.user_id")
    workspace_memberships: Mapped[List["WorkspaceMember"]] = relationship(back_populates="user", foreign_keys="WorkspaceMember.user_id")
    sessions: Mapped[List["Session"]] = relationship(back_populates="user")
    owned_orgs: Mapped[List["OrganizationMember"]] = relationship(foreign_keys="OrganizationMember.invited_by")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # hex color
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # lucide icon name
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="workspaces")
    members: Mapped[List["WorkspaceMember"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    sessions: Mapped[List["Session"]] = relationship(back_populates="workspace")
    mcp_configs: Mapped[List["McpConfig"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_ws_member"),
        Index("ix_ws_member_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="workspace_memberships")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Novo Chat", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="chat", nullable=False)
    speed: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    metadata_: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")
    workspace: Mapped[Optional["Workspace"]] = relationship(back_populates="sessions")
    messages: Mapped[List["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="messages")


class McpConfig(Base):
    __tablename__ = "mcp_configs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="stdio", nullable=False)  # stdio, sse
    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    args: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    env: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON object
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="mcp_configs")


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)  # path in storage
    storage_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)  # local, s3, r2
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256
    metadata_: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStepStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskRunStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON (model, mode, speed, etc.)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON (planned steps)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON (final result)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    steps: Mapped[List["TaskStep"]] = relationship(back_populates="task", cascade="all, delete-orphan", order_by="TaskStep.step_index")
    runs: Mapped[List["TaskRun"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    artifacts: Mapped[List["Artifact"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    approvals: Mapped[List["Approval"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class TaskStep(Base):
    __tablename__ = "task_steps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # agent type
    agent_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStepStatus] = mapped_column(SQLEnum(TaskStepStatus), default=TaskStepStatus.PENDING, nullable=False)
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    output_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task: Mapped["Task"] = relationship(back_populates="steps")
    runs: Mapped[List["TaskRun"]] = relationship(back_populates="step", cascade="all, delete-orphan")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("task_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[TaskRunStatus] = mapped_column(SQLEnum(TaskRunStatus), default=TaskRunStatus.PENDING, nullable=False)
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    output_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of log entries
    checkpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON (serialized state for resume)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task: Mapped["Task"] = relationship(back_populates="runs")
    step: Mapped[Optional["TaskStep"]] = relationship(back_populates="runs")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("task_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("task_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # image, docx, pdf, pptx, xlsx, csv, zip, audio, video, report
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["Task"] = relationship(back_populates="artifacts")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("task_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    decided_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # send_email, publish, delete, etc.
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, critical
    status: Mapped[ApprovalStatus] = mapped_column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task: Mapped["Task"] = relationship(back_populates="approvals")