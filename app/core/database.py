# app/core/database.py
import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devagent:devagent@localhost:5432/devagent")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=os.getenv("DATABASE_ECHO", "false").lower()=="true")
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), unique=True, index=True, nullable=False)
    repository = Column(String(500), index=True, nullable=False)
    pr_number = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (Index("idx_repo_pr", "repository", "pr_number"),)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), index=True, nullable=False)
    overall_assessment = Column(Text)
    security_findings = Column(JSONB, default=[])
    quality_issues = Column(JSONB, default=[])
    test_recommendations = Column(JSONB, default=[])
    documentation_gaps = Column(JSONB, default=[])
    confidence_score = Column(Integer, default=85)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
