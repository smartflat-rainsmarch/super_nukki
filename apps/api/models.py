import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import relationship


class UUIDString(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        return value

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=True)  # nullable for social login
    plan_type = Column(
        Enum("free", "basic", "pro", name="plan_type_enum"),
        default="free",
        nullable=False,
    )
    auth_provider = Column(String(20), default="email", nullable=False)
    provider_id = Column(String(255), nullable=True)
    name = Column(String(100), nullable=True)
    profile_image = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    projects = relationship("Project", back_populates="user")
    billing = relationship("Billing", back_populates="user", uselist=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    user_id = Column(UUIDString, ForeignKey("users.id"), nullable=True)
    image_url = Column(Text, nullable=False)
    status = Column(
        Enum("pending", "processing", "done", "failed", name="project_status_enum"),
        default="pending",
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="projects")
    layers = relationship("Layer", back_populates="project")
    jobs = relationship("Job", back_populates="project")


class Layer(Base):
    __tablename__ = "layers"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    project_id = Column(
        UUIDString, ForeignKey("projects.id"), nullable=False
    )
    type = Column(
        Enum("text", "button", "image", "icon", "card", "background", name="layer_type_enum"),
        nullable=False,
    )
    position = Column(JSON, nullable=True)
    image_url = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    z_index = Column(Integer, default=0, nullable=False)

    project = relationship("Project", back_populates="layers")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    project_id = Column(
        UUIDString, ForeignKey("projects.id"), nullable=False
    )
    status = Column(
        Enum(
            "queued",
            "preprocessing",
            "analyzing",
            "segmenting",
            "inpainting",
            "composing",
            "exporting",
            "completed",
            "failed",
            name="job_status_enum",
        ),
        default="queued",
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="jobs")


class Billing(Base):
    __tablename__ = "billing"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    user_id = Column(
        UUIDString, ForeignKey("users.id"), unique=True, nullable=False
    )
    plan = Column(
        Enum("free", "basic", "pro", name="billing_plan_enum"),
        default="free",
        nullable=False,
    )
    usage_count = Column(Integer, default=0, nullable=False)
    reset_date = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="billing")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified = Column(Integer, default=0, nullable=False)  # 0=pending, 1=verified
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class IpUsage(Base):
    __tablename__ = "ip_usage"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    usage_count = Column(Integer, default=0, nullable=False)
    reset_date = Column(DateTime(timezone=True), nullable=True)


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    name = Column(String(100), nullable=False)
    owner_id = Column(UUIDString, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("TeamMember", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(UUIDString, primary_key=True, default=new_uuid)
    team_id = Column(UUIDString, ForeignKey("teams.id"), nullable=False)
    user_id = Column(UUIDString, ForeignKey("users.id"), nullable=False)
    role = Column(
        Enum("owner", "admin", "member", name="team_role_enum"),
        default="member",
        nullable=False,
    )
    joined_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User")
