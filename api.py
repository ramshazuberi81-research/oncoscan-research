"""
OncosenseAI — Module 5 API (Updated)
======================================
FastAPI REST endpoint wrapping the GenomicRiskEngine.

New in this version
-------------------
- CHASRequest schema — structured CHAS comorbidity input
- AssessRequest extended with chas field
- POST /assess now returns chas_result in RiskReport output
- GET /variants/{name} returns amp_tier and amp_rationale
- POST /parse-report now returns amp_tiers and detected_pharma
- GET /amp-tiers — lists all AMP/ASCO/CAP tier assignments in the database
- GET /chas — documents CHAS scoring items and modifiers

Run locally:
    pip install -r requirements.txt
    uvicorn api:app --reload --port 8000

Author: Ramsha Zuberi, MBBCh, BDS
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from genomic_risk_engine import (
    GenomicRiskEngine,
    PatientProfile,
    CHASProfile,
    VARIANT_DATABASE,
    PHARMACOGENOMICS_DATABASE,
    CHAS_ITEMS,
    CHAS_RISK_MODIFIERS,
    compute_chas_modifier,
    interpret_chas,
)

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(
    title="OncosenseAI — Module 5 API",
    description=(
        "Genomic risk stratification and pharmacogenomic profiling for "
        "early detection of pancreatic, gastric, and esophageal cancers. "
        "AMP/ASCO/CAP variant classification · CHAS comorbidity scoring · "
        "NICE NG12 symptom integration · CPIC pharmacogenomics. "
        "RESEARCH PROTOTYPE — Not for clinical use."
    ),
    version="2.0.0",
    contact={
        "name":  "Ramsha Zuberi, MBBCh, BDS",
        "email": "ramshazuberi81@gmail.com",
        "url":   "https://github.com/ramshazuberi81-research/oncoscan-research",
    },
    license_info={"name": "MIT — Research Use Only"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = GenomicRiskEngine()


# ─────────────────────────────────────────────
# REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class CHASRequest(BaseModel):
    """
    CHAS comorbidity profile — adapted for GI oncology risk modification.
    Each field maps to a scored comorbidity item.
    Stroke/TIA is weighted ×2; all others ×1.
    """
    coronary_heart_disease:      bool = Field(False, description="Coronary heart disease (CHD)")
    hypertension:                bool = Field(False, description="Hypertension (H)")
    age_gte_65:                  bool = Field(False, description="Age ≥ 65 (A)")
    stroke_or_tia:               bool = Field(False, description="Stroke or TIA — weighted ×2 (S)")
    diabetes_mellitus:           bool = Field(False, description="Diabetes mellitus")
    ckd_renal_impairment:        bool = Field(False, description="CKD / renal impairment")
    h_pylori:                    bool = Field(False, description="H. pylori positive (synced with patient profile)")
    ibd_chronic_gi_inflammation: bool = Field(False, description="IBD / chronic GI inflammation")

    class Config:
        schema_extra = {
            "example": {
                "coronary_heart_disease": False,
                "hypertension": True,
                "age_gte_65": False,
                "stroke_or_tia": False,
                "diabetes_mellitus": True,
                "ckd_renal_impairment": False,
                "h_pylori": True,
                "ibd_chronic_gi_inflammation": False,
            }
        }


class AssessRequest(BaseModel):
    """Full genomic risk assessment request — now includes CHAS."""
    age_group:      str = Field(..., example="51-60",
                                description="'< 30' | '30-40' | '41-50' | '51-60' | '61-70' | '> 70'")
    sex:            str = Field(..., example="Female",
                                description="'Female' | 'Male' | 'Other'")
    family_history: str = Field(..., example="Multiple relatives",
                                description="'None' | 'First-degree' | 'Multiple relatives' | 'Known hereditary syndrome'")
    smoking:        bool = Field(False, example=False)
    alcohol:        bool = Field(False, example=False)
    bmi_obese:      bool = Field(False, example=False)
    h_pylori:       bool = Field(False, example=True)

    variants: list[str] = Field(
        ..., example=["BRCA2", "CDH1"],
        description="List of pathogenic variant names (AMP/ASCO/CAP classified)"
    )
    symptoms: list[str] = Field(
        [], example=["weight_loss", "early_satiety"],
        description="Symptom IDs from NICE NG12 alarm features"
    )
    pharma_variants: dict[str, list[str]] = Field(
        {}, example={"DPYD": ["DPYD*2A"]},
        description="Detected pharmacogenomic variants by enzyme"
    )
    chas: CHASRequest = Field(
        default_factory=CHASRequest,
        description="CHAS comorbidity profile for GI oncology risk modification"
    )

    class Config:
        schema_extra = {
            "example": {
                "age_group":      "51-60",
                "sex":            "Female",
                "family_history": "Multiple relatives",
                "smoking":        False,
                "alcohol":        False,
                "bmi_obese":      False,
                "h_pylori":       True,
                "variants":       ["BRCA2", "CDH1", "ATM"],
                "symptoms":       ["weight_loss", "early_satiety", "abdominal_pain"],
                "pharma_variants": {"DPYD": ["DPYD*2A"]},
                "chas": {
                    "hypertension":     True,
                    "diabetes_mellitus": True,
                    "h_pylori":          True,
                },
            }
        }


class ParseReportRequest(BaseModel):
    report_text: str = Field(
        ...,
        description="Raw text from 23andMe, AncestryDNA, or VCF export. "
                    "Returns detected genomic variants, AMP tiers, and pharmacogenomic variants."
    )


class CHASScoreRequest(BaseModel):
    """Standalone CHAS score calculation request."""
    coronary_heart_disease:      bool = False
    hypertension:                bool = False
    age_gte_65:                  bool = False
    stroke_or_tia:               bool = False
    diabetes_mellitus:           bool = False
    ckd_renal_impairment:        bool = False
    h_pylori:                    bool = False
    ibd_chronic_gi_inflammation: bool = False


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """API health check."""
    return {
        "status":    "ok",
        "module":    "OncosenseAI Module 5 — Genomic Risk Engine",
        "version":   "2.0.0",
        "features":  ["AMP/ASCO/CAP tiers", "CHAS comorbidity scoring", "CPIC pharmacogenomics", "NICE NG12 symptoms"],
        "disclaimer": engine.DISCLAIMER,
    }


@app.post("/assess", tags=["Risk Assessment"])
def assess(req: AssessRequest):
    """
    Run a full genomic risk assessment.

    Integrates:
    - AMP/ASCO/CAP variant burden (Tier I–IV classification)
    - CHAS comorbidity scoring (8-item GI-oncology adapted profile)
    - NICE NG12 alarm symptom profile
    - Demographic modifiers (age, sex, family history, lifestyle)
    - CPIC pharmacogenomic flags

    Returns a structured RiskReport with composite score, tier,
    cancer-specific scores, AMP classifications, and clinical recommendations.
    """
    try:
        patient = PatientProfile(
            age_group      = req.age_group,
            sex            = req.sex,
            family_history = req.family_history,
            smoking        = req.smoking,
            alcohol        = req.alcohol,
            bmi_obese      = req.bmi_obese,
            h_pylori       = req.h_pylori,
        )
        chas = CHASProfile(
            coronary_heart_disease      = req.chas.coronary_heart_disease,
            hypertension                = req.chas.hypertension,
            age_gte_65                  = req.chas.age_gte_65,
            stroke_or_tia               = req.chas.stroke_or_tia,
            diabetes_mellitus           = req.chas.diabetes_mellitus,
            ckd_renal_impairment        = req.chas.ckd_renal_impairment,
            h_pylori                    = req.chas.h_pylori or req.h_pylori,
            ibd_chronic_gi_inflammation = req.chas.ibd_chronic_gi_inflammation,
        )
        report = engine.assess(
            patient         = patient,
            variants        = req.variants,
            symptoms        = req.symptoms,
            pharma_variants = req.pharma_variants,
            chas            = chas,
        )
        return engine.report_to_dict(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse-report", tags=["Risk Assessment"])
def parse_report(req: ParseReportRequest):
    """
    Auto-detect pathogenic variants AND pharmacogenomic variants from raw genetic report text.
    Supports 23andMe, AncestryDNA, and VCF-format exports.
    Returns detected variants with AMP/ASCO/CAP tier assignments.
    """
    result = engine.parse_report_text(req.report_text)
    return {
        "detected_variants":    result["detected_variants"],
        "amp_tiers":            result["amp_tiers"],
        "detected_pharma":      result["detected_pharma"],
        "variant_count":        result["variant_count"],
        "pharma_enzyme_count":  result["pharma_enzyme_count"],
        "message": (
            f"Detected {result['variant_count']} genomic variant(s) and "
            f"{result['pharma_enzyme_count']} pharmacogenomic enzyme variant(s)."
        ),
    }


@app.post("/chas/score", tags=["CHAS"])
def chas_score(req: CHASScoreRequest):
    """
    Standalone CHAS comorbidity score calculation.
    Returns score, risk modifier, and clinical interpretation.
    """
    profile = CHASProfile(
        coronary_heart_disease      = req.coronary_heart_disease,
        hypertension                = req.hypertension,
        age_gte_65                  = req.age_gte_65,
        stroke_or_tia               = req.stroke_or_tia,
        diabetes_mellitus           = req.diabetes_mellitus,
        ckd_renal_impairment        = req.ckd_renal_impairment,
        h_pylori                    = req.h_pylori,
        ibd_chronic_gi_inflammation = req.ibd_chronic_gi_inflammation,
    )
    sc = profile.score()
    return {
        "chas_score":    sc,
        "modifier":      profile.modifier(),
        "interpretation": profile.interpretation(),
        "active_items":  profile.active_items(),
        "scoring_breakdown": {
            item: {
                "active":  getattr(profile, item),
                "points":  CHAS_ITEMS[item]["score"],
                "label":   CHAS_ITEMS[item]["label"],
                "rationale": CHAS_ITEMS[item]["rationale"],
            }
            for item in CHAS_ITEMS
        },
    }


@app.get("/chas", tags=["CHAS"])
def get_chas_info():
    """
    Document the CHAS comorbidity scoring system as adapted for GI oncology.
    Lists all 8 scored items, their weights, rationale, and risk modifier thresholds.
    """
    return {
        "description": (
            "CHAS is a GI-oncology adaptation of the CHA2DS2-VASc framework. "
            "It integrates cardiovascular, metabolic, and GI-specific comorbidities "
            "as a multiplicative risk modifier on top of genomic and demographic inputs."
        ),
        "reference": "Adapted from Lip GY et al. Chest. 2010 [CHA2DS2-VASc]; "
                     "GI-oncology extension by OncosenseAI Module 5.",
        "items": [
            {
                "key":       key,
                "label":     data["label"],
                "score":     data["score"],
                "rationale": data["rationale"],
            }
            for key, data in CHAS_ITEMS.items()
        ],
        "modifier_thresholds": [
            {"score_range": f"{lo}–{hi if hi < 99 else '+'}", "modifier": mod}
            for (lo, hi), mod in CHAS_RISK_MODIFIERS.items()
        ],
    }


@app.get("/variants", tags=["Database"])
def list_variants():
    """List all pathogenic variants with AMP/ASCO/CAP tier classifications."""
    return {
        "variants": [
            {
                "name":               name,
                "gene_full":          data["gene_full"],
                "mechanism":          data["mechanism"],
                "inheritance":        data["inheritance"],
                "amp_tier":           data["amp_tier"].value,
                "amp_rationale":      data["amp_rationale"],
                "targeted_agents":    data.get("targeted_agents", []),
                "associated_cancers": [c.value for c in data["associated_cancers"]],
                "population_frequency": data["population_frequency"],
            }
            for name, data in VARIANT_DATABASE.items()
        ],
        "count": len(VARIANT_DATABASE),
    }


@app.get("/variants/{variant_name}", tags=["Database"])
def get_variant(variant_name: str):
    """Get full details for a single variant including AMP/ASCO/CAP classification."""
    data = VARIANT_DATABASE.get(variant_name.upper())
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{variant_name}' not found. Available: {list(VARIANT_DATABASE.keys())}"
        )
    return {
        "name":               variant_name.upper(),
        "gene_full":          data["gene_full"],
        "mechanism":          data["mechanism"],
        "inheritance":        data["inheritance"],
        "amp_tier":           data["amp_tier"].value,
        "amp_rationale":      data["amp_rationale"],
        "targeted_agents":    data.get("targeted_agents", []),
        "associated_cancers": [c.value for c in data["associated_cancers"]],
        "risk_multipliers":   {ct.value: m for ct, m in data["risk_multipliers"].items()},
        "population_frequency": data["population_frequency"],
        "clinical_note":      data["clinical_note"],
        "reference":          data["reference"],
    }


@app.get("/amp-tiers", tags=["Database"])
def list_amp_tiers():
    """
    List all AMP/ASCO/CAP tier assignments in the variant database.
    Groups variants by tier for quick clinical reference.
    """
    tiers: dict[str, list] = {"I": [], "II": [], "III": [], "IV": []}
    for name, data in VARIANT_DATABASE.items():
        tier = data["amp_tier"].value
        tiers[tier].append({
            "variant":      name,
            "gene_full":    data["gene_full"],
            "amp_rationale": data["amp_rationale"][:120] + "...",
        })
    return {
        "description": (
            "AMP/ASCO/CAP 2017 somatic variant interpretation guidelines adapted for germline context. "
            "Tier I: strong clinical significance. Tier II: potential significance. "
            "Tier III: variant of uncertain significance. Tier IV: likely benign."
        ),
        "reference": "Li MM et al. J Mol Diagn. 2017;19(1):4-23.",
        "tiers": tiers,
        "counts": {t: len(v) for t, v in tiers.items()},
    }


@app.get("/pharmacogenomics", tags=["Database"])
def list_pharmacogenomics():
    """List all pharmacogenomic enzyme entries with CPIC guidelines and affected drugs."""
    return {
        "enzymes": [
            {
                "enzyme":                      name,
                "enzyme_full":                 data["enzyme_full"],
                "affected_drugs":              data["affected_drugs"],
                "clinical_relevance_oncology": data["clinical_relevance_oncology"],
                "cpic_guideline":              data["cpic_guideline"],
            }
            for name, data in PHARMACOGENOMICS_DATABASE.items()
        ],
        "count": len(PHARMACOGENOMICS_DATABASE),
    }


@app.get("/pharmacogenomics/{enzyme}", tags=["Database"])
def get_enzyme(enzyme: str):
    """Get full pharmacogenomic details for a single enzyme."""
    data = PHARMACOGENOMICS_DATABASE.get(enzyme.upper())
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Enzyme '{enzyme}' not found. Available: {list(PHARMACOGENOMICS_DATABASE.keys())}"
        )
    return {"enzyme": enzyme.upper(), **data}


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
