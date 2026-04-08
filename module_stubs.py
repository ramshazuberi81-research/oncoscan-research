"""
Temporary stubs — replace each body with your real implementation.
Loaded automatically by orchestrator.py when real modules are absent.
"""


def run_symptom_engine(age_group, sex, symptoms, family_history, smoking, alcohol) -> dict:
    return {
        "ensemble_risk_score": 0.72,
        "top_cancer": "Colorectal",
        "confidence": 0.85,
        "red_flag_count": 3
    }


def run_visual_ai(image_data: str) -> dict:
    return {
        "anomaly_detected": True,
        "hypothesis": "Colorectal",
        "confidence": 0.78,
        "modality": "CT"
    }


def run_treatment_matcher(cancer_hypothesis: str, variant_list: list) -> dict:
    return {
        "recommended_treatment": "FOLFOX + Bevacizumab",
        "guideline_source": "NCCN 2024",
        "genomic_marker_aligned": True,
        "alternatives": ["FOLFIRI", "Capecitabine"]
    }


def generate_pdf_report(data: dict) -> str:
    report_path = f"reports/{data['patient_id']}_report.pdf"
    print(f"[STUB] PDF would be generated at: {report_path}")
    return report_path


def load_model(model_dir: str):
    model = None
    feature_names = ["BRCA1", "MLH1", "MSH2", "TP53", "KRAS"]
    metadata = {"version": "stub"}
    return model, feature_names, metadata


def score_patient(model, variant_list, symptom_list, age_group,
                  sex, family_history, smoking, alcohol, feature_names) -> dict:
    return {
        "composite_risk": 74,
        "risk_tier": "High",
        "contributing_factors": variant_list
    }