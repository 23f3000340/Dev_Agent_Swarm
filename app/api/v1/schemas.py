# app/api/v1/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class CodeFile(BaseModel):
    name: str
    language: str
    changes: int
    content: Optional[str] = None

class AnalyzePRRequest(BaseModel):
    repository: str
    pr_number: int
    files: List[CodeFile]
    context: Optional[str] = ""
    branch: Optional[str] = None
    author: Optional[str] = None

class SecurityFinding(BaseModel):
    severity: str
    title: str
    description: str
    file: str
    line: Optional[int] = None
    recommendation: str

class QualityIssue(BaseModel):
    category: str
    severity: str
    file: str
    description: str
    suggestion: str

class AnalyzePRResponse(BaseModel):
    request_id: str
    status: str
    overall_assessment: str
    security_findings: List[SecurityFinding] = []
    quality_issues: List[QualityIssue] = []
    test_recommendations: List[str] = []
    documentation_gaps: List[str] = []
    confidence_score: float = Field(0.85, ge=0, le=1)
