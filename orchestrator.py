import importlib
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dde_module import DDERequest, DiagnosticDissonanceEngine, TemporalSignal
from adapters import (
    module5_to_genomic_signal,
    module1_to_symptom_signal,
    module3_to_treatment_signal,
    module2_to_visual_signal,
)
import module_stubs

# ── Module runners ────────────────────────────────────────────────────────────
# Each module is resolved on its own: the real implementation is used if its
# file exists, otherwise the stub is used. MODULE_SOURCE records which, so the
# API never silently presents stub output as real module output.
MODULE_SOURCE: dict = {}


def _resolve(label: str, real_module: str, names: list):
    try:
        mod = importlib.import_module(real_module)
        funcs = [getattr(mod, n) for n in names]
        MODULE_SOURCE[label] = "real"
    except (ImportError, AttributeError):
        funcs = [getattr(module_stubs, n) for n in names]
        MODULE_SOURCE[label] = "stub"
    return funcs[0] if len(funcs) == 1 else funcs


run_symptom_engine = _resolve("M1_symptom", "module1_symptom", ["run_symptom_engine"])
run_visual_ai = _resolve("M2_visual", "module2_visual", ["run_visual_ai"])
run_treatment_matcher = _resolve("M3_treatment", "module3_treatment", ["run_treatment_matcher"])
generate_pdf_report = _resolve("M4_report", "module4_report", ["generate_pdf_report"])
score_patient, load_model = _resolve(
    "M5_genomic", "genomic_risk_engine", ["score_patient", "load_model"]
)
# ─────────────────────────────────────────────────────────────────────────────

MODEL_DIR = os.environ.get("ONCOSENSE_MODEL_DIR", "oncosense_module5/")
_model_cache: dict = {}


def get_genomic_model():
    """Load the Module 5 model once and reuse it across requests."""
    if "loaded" not in _model_cache:
        _model_cache["loaded"] = load_model(MODEL_DIR)
    model, feature_names, _ = _model_cache["loaded"]
    return model, feature_names


app = FastAPI(title="OncosenseAI — Unified Pipeline", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prototype only; restrict before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
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
    module_sources: dict  # "real" or "stub" for each module
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
        alcohol=req.alcohol,
    )

    # ── MODULE 2: Visual AI (rule-based) ──────────────────
    m2_result = run_visual_ai(req.image_data) if req.image_data else None

    # ── MODULE 3: Treatment matcher ───────────────────────
    m3_result = run_treatment_matcher(
        cancer_hypothesis=m1_result["top_cancer"],
        variant_list=req.variant_list,
    )

    # ── MODULE 5: Genomic risk engine ─────────────────────
    model, feature_names = get_genomic_model()
    m5_result = score_patient(
        model=model,
        variant_list=req.variant_list,
        symptom_list=req.symptoms,
        age_group=req.age_group,
        sex=req.sex,
        family_history=req.family_history,
        smoking=req.smoking,
        alcohol=req.alcohol,
        feature_names=feature_names,
    )

    # ── ADAPTERS ──────────────────────────────────────────
    genomic_signal = module5_to_genomic_signal(m5_result, req.variant_list, req.her2_status)
    symptom_signal = module1_to_symptom_signal(m1_result)
    treatment_signal = module3_to_treatment_signal(m3_result)
    visual_signal = module2_to_visual_signal(m2_result) if m2_result else None

    temporal_signal = TemporalSignal(
        visits=req.visits,
        trajectory_deviation_score=req.trajectory_deviation_score,
        new_signals_since_last_visit=req.new_signals,
    )

    # ── MODULE 6: Diagnostic Dissonance Engine ────────────
    dde_request = DDERequest(
        patient_id=req.patient_id,
        genomic=genomic_signal,
        symptom=symptom_signal,
        visual=visual_signal,
        treatment=treatment_signal,
        temporal=temporal_signal,
    )
    dde_response = engine.analyze(dde_request)
    dde_dict = dde_response.model_dump()  # pydantic v2 (.dict() is deprecated)

    # ── MODULE 4: PDF report ──────────────────────────────
    pdf_path = generate_pdf_report({
        "patient_id": req.patient_id,
        "m1": m1_result,
        "m5": m5_result,
        "m6": dde_dict,
    })

    return PipelineResponse(
        patient_id=req.patient_id,
        module_sources=MODULE_SOURCE,
        m1_symptom=m1_result,
        m2_visual=m2_result,
        m3_treatment=m3_result,
        m5_genomic=m5_result,
        m6_dde=dde_dict,
        pdf_report_path=pdf_path,
    )


@app.get("/api/v1/pipeline/health")
async def health():
    return {"status": "operational", "module_sources": MODULE_SOURCE}


if __name__ == "__main__":
    uvicorn.run("orchestrator:app", host="0.0.0.0", port=8000, reload=True)
