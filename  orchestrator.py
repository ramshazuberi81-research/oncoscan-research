from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from dde_module import DDERequest, DiagnosticDissonanceEngine, TemporalSignal
from adapters import (
    module5_to_genomic_signal,
    module1_to_symptom_signal,
    module3_to_treatment_signal,
    module2_to_visual_signal
)

# ── Module runners: real modules take priority, stubs used as fallback ────────
try:
    from module1_symptom import run_symptom_engine
    from module2_visual import run_visual_ai
    from module3_treatment import run_treatment_matcher
    from module4_report import generate_pdf_report
    from genomic_risk_engine import score_patient, load_model
except ImportError:
    from module_stubs import (
        run_symptom_engine,
        run_visual_ai,
        run_treatment_matcher,
        generate_pdf_report,
        score_patient,
        load_model
    )
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="OncosenseAI — Unified Pipeline", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

engine = DiagnosticDissonanceEngine()


class PipelineRequest(BaseModel):
    patient_id: str
    age_group: str
    sex: str
    symptoms: list[str]
    family_history: str = "none"
    smoking: bool = False
    alcohol: bool = False
    image_data: Optional[str] = None
    variant_list: list[str] = []
    her2_status: str = "Negative"
    visits: int = 1
    trajectory_deviation_score: float = 0.0
    new_signals: list[str] = []


class PipelineResponse(BaseModel):
    patient_id: str
    m1_symptom: dict
    m2_visual: Optional[dict]
    m3_treatment: dict
    m5_genomic: dict
    m6_dde: dict
    pdf_report_path: Optional[str]


@app.post("/api/v1/pipeline/analyze", response_model=PipelineResponse)
async def run_full_pipeline(req: PipelineRequest):

    # ── MODULE 1: Symptom engine ──────────────────────────
    m1_result = run_symptom_engine(
        age_group=req.age_group,
        sex=req.sex,
        symptoms=req.symptoms,
        family_history=req.family_history,
        smoking=req.smoking,
        alcohol=req.alcohol
    )

    # ── MODULE 2: Visual AI ───────────────────────────────
    m2_result = None
    if req.image_data:
        m2_result = run_visual_ai(req.image_data)

    # ── MODULE 3: Treatment matcher ───────────────────────
    m3_result = run_treatment_matcher(
        cancer_hypothesis=m1_result["top_cancer"],
        variant_list=req.variant_list
    )

    # ── MODULE 5: Genomic risk engine ─────────────────────
    model, feature_names, _ = load_model("oncosense_module5/")
    m5_result = score_patient(
        model=model,
        variant_list=req.variant_list,
        symptom_list=req.symptoms,
        age_group=req.age_group,
        sex=req.sex,
        family_history=req.family_history,
        smoking=req.smoking,
        alcohol=req.alcohol,
        feature_names=feature_names
    )

    # ── ADAPTERS ──────────────────────────────────────────
    genomic_signal   = module5_to_genomic_signal(m5_result, req.variant_list, req.her2_status)
    symptom_signal   = module1_to_symptom_signal(m1_result)
    treatment_signal = module3_to_treatment_signal(m3_result)
    visual_signal    = module2_to_visual_signal(m2_result) if m2_result else None

    temporal_signal = TemporalSignal(
        visits=req.visits,
        trajectory_deviation_score=req.trajectory_deviation_score,
        new_signals_since_last_visit=req.new_signals
    )

    # ── MODULE 6: Diagnostic Dissonance Engine ────────────
    dde_request = DDERequest(
        patient_id=req.patient_id,
        genomic=genomic_signal,
        symptom=symptom_signal,
        visual=visual_signal,
        treatment=treatment_signal,
        temporal=temporal_signal
    )
    dde_response = engine.analyze(dde_request)

    # ── MODULE 4: PDF report ──────────────────────────────
    pdf_path = generate_pdf_report({
        "patient_id": req.patient_id,
        "m1": m1_result,
        "m5": m5_result,
        "m6": dde_response.dict()
    })

    return PipelineResponse(
        patient_id=req.patient_id,
        m1_symptom=m1_result,
        m2_visual=m2_result,
        m3_treatment=m3_result,
        m5_genomic=m5_result,
        m6_dde=dde_response.dict(),
        pdf_report_path=pdf_path
    )


@app.get("/api/v1/pipeline/health")
async def health():
    return {"status": "operational", "modules": ["M1", "M2", "M3", "M4", "M5", "M6"]}


if __name__ == "__main__":
    uvicorn.run("orchestrator:app", host="0.0.0.0", port=8000, reload=True)