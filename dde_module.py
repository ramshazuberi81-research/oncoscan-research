from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class DissonanceLevel(Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GenomicSignal:
    disturbance_score: float
    mutations_detected: List[str]
    msi_status: str                        # "MSI-H" | "MSS"
    her2_status: str                       # "Positive" | "Negative"
    pd_l1_cps: Optional[float]
    pharmacogenomic_conflicts: List[str] = field(default_factory=list)


@dataclass
class SymptomSignal:
    ensemble_risk_score: float
    primary_cancer_hypothesis: str
    symptom_confidence: float
    red_flag_count: int = 0


@dataclass
class VisualSignal:
    visual_anomaly_detected: bool = False
    visual_cancer_hypothesis: Optional[str] = None
    visual_confidence: float = 0.0
    imaging_modality: str = "Unknown"


@dataclass
class TreatmentSignal:
    recommended_treatment: str
    guideline_source: str
    genomic_marker_aligned: bool = True
    alternative_treatments: List[str] = field(default_factory=list)


@dataclass
class TemporalSignal:
    visits: int = 1
    trajectory_deviation_score: float = 0.0
    new_signals_since_last_visit: List[str] = field(default_factory=list)


@dataclass
class DDERequest:
    patient_id: str
    genomic: GenomicSignal
    symptom: SymptomSignal
    treatment: TreatmentSignal
    temporal: TemporalSignal
    visual: Optional[VisualSignal] = None


@dataclass
class DissonanceFinding:
    signal_pair: str
    conflict_description: str
    severity: float
    recommendation: str


@dataclass
class DDEResponse:
    patient_id: str
    dissonance_level: DissonanceLevel
    overall_dissonance_score: float
    findings: List[DissonanceFinding]
    escalate: bool
    summary: str

    def dict(self):
        return {
            "patient_id": self.patient_id,
            "dissonance_level": self.dissonance_level.value,
            "overall_dissonance_score": self.overall_dissonance_score,
            "findings": [
                {
                    "signal_pair": f.signal_pair,
                    "conflict_description": f.conflict_description,
                    "severity": f.severity,
                    "recommendation": f.recommendation
                }
                for f in self.findings
            ],
            "escalate": self.escalate,
            "summary": self.summary
        }


class DiagnosticDissonanceEngine:

    def analyze(self, req: DDERequest) -> DDEResponse:
        findings = []
        scores = []

        # ── Check 1: Genomic vs Symptom ──────────────────
        g_score = req.genomic.disturbance_score
        s_score = req.symptom.ensemble_risk_score
        delta = abs(g_score - s_score)

        if delta > 0.4:
            findings.append(DissonanceFinding(
                signal_pair="genomic vs symptom",
                conflict_description=(
                    f"Genomic disturbance ({g_score:.2f}) and symptom risk "
                    f"({s_score:.2f}) diverge by {delta:.2f}"
                ),
                severity=delta,
                recommendation="Order confirmatory biopsy or extended panel sequencing."
            ))
        scores.append(delta)

        # ── Check 2: Treatment alignment ─────────────────
        if not req.treatment.genomic_marker_aligned:
            findings.append(DissonanceFinding(
                signal_pair="treatment vs genomic",
                conflict_description="Recommended treatment is not aligned with detected genomic markers.",
                severity=0.7,
                recommendation="Review treatment protocol against current genomic profile."
            ))
            scores.append(0.7)
        else:
            scores.append(0.0)

        # ── Check 3: MSI-H without immunotherapy ─────────
        if (req.genomic.msi_status == "MSI-H" and
                "immunotherapy" not in req.treatment.recommended_treatment.lower()):
            findings.append(DissonanceFinding(
                signal_pair="genomic (MSI) vs treatment",
                conflict_description="MSI-H detected but immunotherapy not in recommended treatment.",
                severity=0.65,
                recommendation="Consider pembrolizumab or nivolumab per NCCN MSI-H guidelines."
            ))
            scores.append(0.65)
        else:
            scores.append(0.0)

        # ── Check 4: Visual vs Symptom ───────────────────
        if req.visual:
            if (req.visual.visual_anomaly_detected and
                    req.symptom.ensemble_risk_score < 0.3):
                findings.append(DissonanceFinding(
                    signal_pair="visual vs symptom",
                    conflict_description=(
                        "Visual anomaly detected but symptom risk score is low "
                        f"({req.symptom.ensemble_risk_score:.2f})."
                    ),
                    severity=0.55,
                    recommendation="Correlate imaging findings with clinical presentation."
                ))
                scores.append(0.55)
            else:
                scores.append(0.0)

        # ── Check 5: Temporal drift ───────────────────────
        if req.temporal.trajectory_deviation_score > 0.6:
            findings.append(DissonanceFinding(
                signal_pair="temporal trajectory",
                conflict_description=(
                    f"Trajectory deviation score {req.temporal.trajectory_deviation_score:.2f} "
                    "indicates rapid clinical progression."
                ),
                severity=req.temporal.trajectory_deviation_score,
                recommendation="Expedite specialist review and repeat imaging within 2 weeks."
            ))
            scores.append(req.temporal.trajectory_deviation_score)
        else:
            scores.append(0.0)

        # ── Aggregate ─────────────────────────────────────
        overall = round(sum(scores) / len(scores), 3) if scores else 0.0

        if overall >= 0.75:
            level = DissonanceLevel.CRITICAL
        elif overall >= 0.55:
            level = DissonanceLevel.HIGH
        elif overall >= 0.35:
            level = DissonanceLevel.MODERATE
        elif overall >= 0.15:
            level = DissonanceLevel.LOW
        else:
            level = DissonanceLevel.NONE

        escalate = level in (DissonanceLevel.HIGH, DissonanceLevel.CRITICAL)

        summary = (
            f"DDE identified {len(findings)} dissonance finding(s) with an overall "
            f"score of {overall:.2f} ({level.value.upper()}). "
            + ("Immediate escalation recommended." if escalate else "Routine monitoring advised.")
        )

        return DDEResponse(
            patient_id=req.patient_id,
            dissonance_level=level,
            overall_dissonance_score=overall,
            findings=findings,
            escalate=escalate,
            summary=summary
        )