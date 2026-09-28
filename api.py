"""HTTP boundary for the evidence-first research workflow."""

from io import BytesIO
import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from evidence_pdf import generate_evidence_pdf
from identity_workflow import run_identity_research
from run_store import delete_all_runs, delete_run, get_run, list_runs, prune_runs, save_run


async def _cleanup_runs():
    while True:
        await asyncio.to_thread(prune_runs)
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_task = asyncio.create_task(_cleanup_runs())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(title="KYCX Research API", docs_url=None, redoc_url=None, lifespan=lifespan)


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
    # A year, not a full date: enough to compare with ages in reports and sanctions lists.
    birth_year: int | None = Field(default=None, ge=1900, le=date.today().year)
    profession: Literal["healthcare", "lawyer", "other", "unknown"] = "unknown"
    # Names the person is known by, comma separated, such as a roepnaam.
    aliases: str = Field(default="", max_length=160)


class PdfRequest(BaseModel):
    report: dict
    analyst: str = Field(default="", max_length=120)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest):
    try:
        report = dict(run_identity_research(
            request.name, request.city, request.employer, request.context,
            birth_year=request.birth_year, profession=request.profession, aliases=request.aliases,
        ))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research provider failed: {type(exc).__name__}") from exc
    try:
        report["saved_run"] = save_run(report)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Check completed but could not be saved. Try again later.") from exc
    return report


@app.get("/runs")
def runs():
    return {"runs": list_runs()}


@app.get("/runs/{run_id}")
def run_detail(run_id: str):
    report = get_run(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Saved run not found or expired.")
    return report


@app.delete("/runs/{run_id}")
def remove_run(run_id: str):
    if not delete_run(run_id):
        raise HTTPException(status_code=404, detail="Saved run not found or expired.")
    return {"deleted": True}


@app.delete("/runs")
def clear_runs():
    return {"deleted": delete_all_runs()}


@app.post("/report.pdf")
def report_pdf(request: PdfRequest):
    data = generate_evidence_pdf(request.report, request.analyst)
    return StreamingResponse(
        BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="person-research-draft.pdf"'},
    )
