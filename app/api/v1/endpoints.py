# app/api/v1/endpoints.py
from fastapi import APIRouter, HTTPException
from uuid import uuid4
from time import perf_counter
from sqlalchemy.orm import Session
from app.core.database import get_db, AnalysisRequest, AnalysisResult
from app.core.bedrock_client import BedrockOrchestrator
from app.api.v1.schemas import AnalyzePRRequest, AnalyzePRResponse

router = APIRouter()

def _format_pr_prompt(req: AnalyzePRRequest) -> str:
    file_list = "\n".join([f"- {f.name} ({f.language}): {f.changes} changes" for f in req.files])
    return (
        f"Analyze this GitHub PR concisely:\n"
        f"Repo: {req.repository}\nPR: {req.pr_number}\n"
        f"Files:\n{file_list}\n\nContext:\n{req.context or ''}\n\n"
        "Return a tight summary with:\n"
        "1) Top security risks\n2) Code quality issues\n3) Test ideas\n4) Doc gaps\n"
        "Output JSON with keys: overall_assessment, security_findings[], quality_issues[], test_recommendations[], documentation_gaps[]."
    )

@router.post("/analyze/pr", response_model=AnalyzePRResponse)
async def analyze_pr(payload: AnalyzePRRequest, db: Session = next(get_db())):
    req_id = str(uuid4())
    db.add(AnalysisRequest(request_id=req_id, repository=payload.repository, pr_number=payload.pr_number, status="processing"))
    db.commit()

    start = perf_counter()
    try:
        orchestrator = BedrockOrchestrator()
        prompt = _format_pr_prompt(payload)
        result = await orchestrator.invoke_supervisor_agent(session_id=req_id, input_text=prompt)
        assessment = result.get("assessment", "").strip()

        # Persist minimal result first (raw)
        db.add(AnalysisResult(request_id=req_id, overall_assessment=assessment, confidence_score=85))
        db.commit()

        elapsed_ms = int((perf_counter() - start) * 1000)
        return AnalyzePRResponse(
            request_id=req_id,
            status="success",
            overall_assessment=assessment or "Analysis completed.",
            test_recommendations=[],
            documentation_gaps=[],
            security_findings=[],
            quality_issues=[],
            confidence_score=0.85,
        )
    except Exception as e:
        db.query(AnalysisRequest).filter_by(request_id=req_id).update({"status": "failed"})
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
