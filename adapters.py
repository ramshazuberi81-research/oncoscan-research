from dde_module import GenomicSignal, SymptomSignal, VisualSignal, TreatmentSignal


def module5_to_genomic_signal(m5_result: dict, variant_list: list, her2_status: str = "Negative") -> GenomicSignal:
    composite = m5_result["composite_risk"]
    disturbance_score = round(composite / 100, 3)

    msi_genes = {"MLH1", "MSH2"}
    msi_status = "MSI-H" if any(v in msi_genes for v in variant_list) else "MSS"

    return GenomicSignal(
        disturbance_score=disturbance_score,
        mutations_detected=variant_list,
        msi_status=msi_status,
        her2_status=her2_status,
        pd_l1_cps=None,
        pharmacogenomic_conflicts=[]
    )


def module1_to_symptom_signal(m1_result: dict) -> SymptomSignal:
    return SymptomSignal(
        ensemble_risk_score=m1_result["ensemble_risk_score"],
        primary_cancer_hypothesis=m1_result["top_cancer"],
        symptom_confidence=m1_result["confidence"],
        red_flag_count=m1_result.get("red_flag_count", 0)
    )


def module3_to_treatment_signal(m3_result: dict) -> TreatmentSignal:
    return TreatmentSignal(
        recommended_treatment=m3_result["recommended_treatment"],
        guideline_source=m3_result["guideline_source"],
        genomic_marker_aligned=m3_result.get("genomic_marker_aligned", True),
        alternative_treatments=m3_result.get("alternatives", [])
    )


def module2_to_visual_signal(m2_result: dict) -> VisualSignal:
    return VisualSignal(
        visual_anomaly_detected=m2_result.get("anomaly_detected", False),
        visual_cancer_hypothesis=m2_result.get("hypothesis"),
        visual_confidence=m2_result.get("confidence", 0.0),
        imaging_modality=m2_result.get("modality", "Unknown")
    )