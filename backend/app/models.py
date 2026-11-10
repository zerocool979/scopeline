from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import deferred, relationship

from .database import Base

ROLES = ("admin", "lead", "tester", "reviewer", "writer")
ENGAGEMENT_STATUS = ("draft", "active", "completed")
FINDING_STATUS = ("open", "fixed", "retest_passed")
REVIEW_STATUS = ("draft", "in_review", "approved", "changes_requested")
RETEST_RESULT = ("passed", "failed", "partial")
REPORT_KINDS = ("pretest", "retest")
TEMPLATE_STATUS = ("draft", "active", "archived")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


engagement_members = Table(
    "engagement_members", Base.metadata,
    Column("engagement_id", ForeignKey("engagements.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class Engagement(Base):
    __tablename__ = "engagements"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    client = Column(String(200), nullable=False)
    scope = Column(Text, default="", nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    roe_text = Column(Text, default="", nullable=False)
    roe_approved = Column(Boolean, default=False, nullable=False)
    roe_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    roe_approved_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="draft", nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    members = relationship("User", secondary=engagement_members)
    roe_approved_by = relationship("User", foreign_keys=[roe_approved_by_id])
    findings = relationship("Finding", cascade="all, delete-orphan", order_by="Finding.number")


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("engagement_id", "number"),)
    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="", nullable=False)
    impact = Column(Text, default="", nullable=False)
    recommendation = Column(Text, default="", nullable=False)
    cvss_vector = Column(String(80), nullable=False)
    cvss_score = Column(Float, nullable=False)
    severity = Column(String(12), nullable=False)
    status = Column(String(16), default="open", nullable=False)
    retest_notes = Column(Text, default="", nullable=False)
    review_status = Column(String(24), default="draft", nullable=False)
    review_note = Column(Text, default="", nullable=False)
    due_date = Column(Date, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    evidence = relationship("Evidence", cascade="all, delete-orphan", order_by="Evidence.id",
                            foreign_keys="Evidence.finding_id", back_populates="finding")
    retests = relationship("Retest", cascade="all, delete-orphan", order_by="Retest.round_no",
                           back_populates="finding")


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    retest_id = Column(Integer, ForeignKey("retests.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_name = Column(String(64), nullable=False)
    content_type = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    data = deferred(Column(LargeBinary, nullable=True))  # terisi bila EVIDENCE_IN_DB=1
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=utcnow, nullable=False)

    finding = relationship("Finding", foreign_keys=[finding_id], back_populates="evidence")
    retest = relationship("Retest", foreign_keys=[retest_id], back_populates="evidence")


class Retest(Base):
    """Satu ronde verifikasi ulang (retest) atas sebuah temuan."""
    __tablename__ = "retests"
    __table_args__ = (UniqueConstraint("finding_id", "round_no"),)
    id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)
    result = Column(String(16), nullable=False)
    tested_at = Column(Date, nullable=False)
    notes = Column(Text, default="", nullable=False)
    tester_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    finding = relationship("Finding", back_populates="retests")
    tester = relationship("User", foreign_keys=[tester_id])
    evidence = relationship("Evidence", foreign_keys="Evidence.retest_id", back_populates="retest",
                            order_by="Evidence.id")


class FindingTemplate(Base):
    __tablename__ = "finding_templates"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="", nullable=False)
    impact = Column(Text, default="", nullable=False)
    recommendation = Column(Text, default="", nullable=False)
    cvss_vector = Column(String(80), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(64), nullable=False, default="-")
    action = Column(String(64), nullable=False)
    entity = Column(String(32), default="", nullable=False)
    entity_id = Column(Integer, nullable=True)
    detail = Column(String(1000), default="", nullable=False)


class NoteTemplate(Base):
    """Templat catatan pentester (Markdown)."""
    __tablename__ = "note_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    content = Column(Text, default="", nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Note(Base):
    """Catatan Markdown per engagement. owner_id NULL = catatan tim; selain itu catatan pribadi penguji."""
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", foreign_keys=[owner_id])
    versions = relationship("NoteVersion", cascade="all, delete-orphan", order_by="NoteVersion.version")


class NoteVersion(Base):
    __tablename__ = "note_versions"
    __table_args__ = (UniqueConstraint("note_id", "version"),)
    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    content = Column(Text, default="", nullable=False)
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    editor = relationship("User", foreign_keys=[edited_by_id])


class ReportTemplate(Base):
    """Templat laporan DOCX berversi per jenis (pretest/retest). Disimpan di database (hosting tanpa disk persisten)."""
    __tablename__ = "report_templates"
    __table_args__ = (UniqueConstraint("kind", "version"),)
    id = Column(Integer, primary_key=True)
    kind = Column(String(16), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String(16), default="draft", nullable=False)
    filename = Column(String(255), nullable=False)
    notes = Column(String(500), default="", nullable=False)
    size = Column(Integer, nullable=False)
    data = deferred(Column(LargeBinary, nullable=False))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
