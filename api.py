"""HTTP boundary for the evidence-first research workflow."""

from io import BytesIO

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from evidence_pdf import generate_evidence_pdf
from identity_workflow import run_identity_research

app = FastAPI(title="KYCX Research API", docs_url=None, redoc_url=None)


@app.middleware("http")
async def no_store(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class ResearchRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    city: str = Field(min_length=2, max_length=120)
    employer: str = Field(default="", max_length=160)
    context: str = Field(default="", max_length=300)


class PdfRequest(BaseModel):
    report: dict
    analyst: str = Field(default="", max_length=120)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest):
    try:
        return run_identity_research(
            request.name, request.city, request.employer, request.context
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research provider failed: {type(exc).__name__}") from exc


@app.post("/report.pdf")
def report_pdf(request: PdfRequest):
    data = generate_evidence_pdf(request.report, request.analyst)
    return StreamingResponse(
        BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="person-research-draft.pdf"'},
    )
