 OncoScan _research
AI-Powered Abdominal Cancer Early Detection Platform

<div align="center">

![Status](https://img.shields.io/badge/Status-Research%20Prototype-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Stage](https://img.shields.io/badge/Stage-Module%201%20Complete-teal?style=for-the-badge)
![Data](https://img.shields.io/badge/Data-SEER%20Validation%20Pending-orange?style=for-the-badge)

Symptom Triage · Imaging AI · Precision Treatment Matching**
*From first symptom to treatment recommendation — one integrated platform*

</div>

---

 The Problem — Same Gap Everywhere

```
         HOUSTON          LONDON           KARACHI          NAIROBI
            🏥               🏥               🏥               🏥
            |                |                |                |
     Patient comes in with vague symptoms: fatigue, weight loss, pain
            |                |                |                |
            ❓               ❓               ❓               ❓
     Doctor has NO tool to know: is this cancer or not?
            |                |                |                |
           ⏳               ⏳               ⏳               ⏳
     Weeks pass. Patient returns. Imaging done. Cancer confirmed.
            |                |                |                |
           💔               💔               💔               💔
                    LATE STAGE — Treatment options limited
```

---

 Why This Matters — The Numbers

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                   │
│   769,000    Gastric cancer deaths per year (WHO 2024)           │
│              ████████████████████████████████████ 769K           │
│                                                                   │
│   2nd        Colorectal cancer — 2nd most common globally        │
│              ██████████████████████████████████████████          │
│                                                                   │
│   >80%       Abdominal cancers diagnosed at LATE stage           │
│              ████████████████████████████████                    │
│                                                                   │
│   $0         Tools bridging symptom → treatment today            │
│              (none exist)                                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Platform Architecture — Three Modules

```
╔══════════════════╗     ╔══════════════════╗     ╔══════════════════╗
║                  ║     ║                  ║     ║                  ║
║    MODULE 1      ║────▶║    MODULE 2      ║────▶║    MODULE 3      ║
║                  ║     ║                  ║     ║                  ║
║  SYMPTOM ENGINE  ║     ║  IMAGING AI      ║     ║  TREATMENT       ║
║                  ║     ║                  ║     ║  MATCHER         ║
║  • NLP symptom   ║     ║  • CT/MRI/US     ║     ║                  ║
║    extraction    ║     ║    analysis      ║     ║  • NCCN/NICE/WHO ║
║  • 17 clinical   ║     ║  • CNN lesion    ║     ║    guidelines    ║
║    variables     ║     ║    detection     ║     ║  • Genomic       ║
║  • Risk scoring  ║     ║  • Radiology     ║     ║    matching      ║
║  • LR+XGB+RF     ║     ║    report gen    ║     ║  • Trial         ║
║    ensemble      ║     ║  • TCIA trained  ║     ║    eligibility   ║
║                  ║     ║                  ║     ║                  ║
║  ✅ BUILT        ║     ║  🔨 IN PROGRESS  ║     ║  📋 PLANNED      ║
╚══════════════════╝     ╚══════════════════╝     ╚══════════════════╝
         │                        │                        │
         ▼                        ▼                        ▼
   Risk Tier Output         Lesion Report          Treatment Plan
   🟢 LOW                   Suspicious finding     First-line therapy
   🟡 ELEVATED              flagged for MDT        + Trial match
   🔴 URGENT                review
```

---

Module 1 — How It Works

Input Features (17 variables)

```
DEMOGRAPHICS          ALARM SYMPTOMS                CLINICAL CONTEXT
─────────────         ──────────────────────────    ────────────────────
• Age                 • Rectal bleeding       🔴    • Symptom duration
• Sex                 • Unexplained wt loss   🔴    • Family history
• BMI                 • Dysphagia             🟠    • Prior GI diagnosis
                      • Abdominal pain        🟡
                      • Change in bowel habit 🟠    🔴 High specificity
                      • Early satiety         🟡    🟠 Medium specificity
                      • Jaundice              🔴    🟡 Lower specificity
                      • Fatigue               🟡
                      • Palpable mass         🔴
                      • Iron deficiency       🟠
                      • Nausea / vomiting     🟡
```

 Model Architecture

```
                    ┌─────────────────────────────────┐
                    │         INPUT FEATURES           │
                    │    (17 clinical variables +      │
                    │     12 engineered features)      │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼───────────────────┐
              │                    │                   │
              ▼                    ▼                   ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  LOGISTIC        │  │    XGBOOST       │  │  RANDOM FOREST   │
   │  REGRESSION      │  │                  │  │                  │
   │  Interpretable   │  │  300 estimators  │  │  200 trees       │
   │  L2 penalty      │  │  depth = 5       │  │  depth = 8       │
   │  weight: 1x      │  │  weight: 2x      │  │  weight: 1x      │
   └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
            │                     │                      │
            └─────────────────────┼──────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────┐
                    │      SOFT VOTING ENSEMBLE        │
                    │   (weighted probability avg)     │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
               🟢 LOW        🟡 ELEVATED      🔴 URGENT
               prob < 15%    prob 15–40%      prob > 40%
               Routine       Non-urgent       2-week-wait
               follow-up     referral         referral
```

---

Performance (Simulated Dataset)

> Real validation on SEER + MIMIC-IV in progress. Results below are prototype only.

ROC Curve

```
Sensitivity
  1.0 ┤                   ╭────────────────────
      │                ╭──╯  ── Ensemble
  0.9 ┤             ╭──╯     ── XGBoost
      │          ╭──╯        ·· Random Forest
  0.8 ┤       ╭──╯           -- Logistic Reg
      │    ╭──╯
  0.7 ┤  ╭─╯
      │ ╭╯
  0.6 ┤╭╯
      ││
  0.5 ┼────────────────────────────── (random)
      0   0.1   0.2   0.3   0.4   0.5
                1 - Specificity →
```

Metrics

```
┌──────────────────────┬────────┬─────────────┬─────────────┬───────┐
│ Model                │ AUROC  │ Sensitivity │ Specificity │  NPV  │
├──────────────────────┼────────┼─────────────┼─────────────┼───────┤
│ Logistic Regression  │  0.84  │    0.95     │    0.52     │  0.98 │
│ XGBoost              │  0.87  │    0.95     │    0.57     │  0.98 │
│ Random Forest        │  0.86  │    0.95     │    0.55     │  0.98 │
│ ✅ Ensemble (Final)  │  0.88  │    0.95     │    0.60     │  0.99 │
└──────────────────────┴────────┴─────────────┴─────────────┴───────┘
  Target sensitivity fixed at 95% — must not miss cancer patients
```
 Feature Importance (SHAP Values)

```
  Palpable Mass         ████████████████████████  most important
  Jaundice              ████████████████████
  Weight Loss           ██████████████████
  Rectal Bleeding       ████████████████
  Age                   ██████████████
  Iron Deficiency       ████████████
  Family History        ██████████
  Change Bowel Habit    ████████
  Alarm Count           ███████
  Symptom Duration      ██████
  Dysphagia             █████
  Age × Alarms          ████      least of top 12
                        └──────────────────────▶
                         Higher bar = more impact on cancer score
```

---

Research Methodology

```
PHASE 1                         PHASE 2                    PHASE 3
Algorithm Development           Prospective Pilot          Multi-Centre
──────────────────────          ──────────────────         ──────────────
Data:                           Setting:                   Scope:
  TCGA (open)                     FQHC (USA)                US + International
  SEER ← applying                 IRB approved              FHIR/HL7 EHR
  MIMIC-IV ← pending              100–200 patients          integration

Validation:                     Output:                    Regulatory:
  80/20 split                     Prospective vs            FDA 510(k)
  5-fold CV                       retrospective             CE Mark EU
  AUROC + calibration             concordance               MDR pathway
  SHAP explainability             SUS usability
                                  Peer-reviewed pub

STATUS: ✅ Simulated            STATUS: 🔨 Seeking          STATUS: 📋 Planned
        🔨 Real data pending            IRB partner
```

---

 Competitive Landscape

```
                     Symptom   Imaging   Treatment   Accessible
                     Triage    AI        Matching    to Primary Care
                     ──────────────────────────────────────────────
Exact Sciences         ✗         ✗          ✗            ✗  ($600)
Grail Galleri          ✗         ✗          ✗            ✗  ($949)
Guardant Health        ✗         ✗        Partial        ✗  ($$$)
Hospital CDSS        Partial   Partial      ✗            ✗  (enterprise)
──────────────────────────────────────────────────────────────────
✅ OncoScan            ✓         ✓          ✓            ✓  (primary care)
──────────────────────────────────────────────────────────────────

OncoScan is the layer BEFORE existing tools —
getting patients to the right test faster and cheaper.
```

---

 Repository Structure

```
oncoscan-research/
│
├── 📓 OncoScan_Colab_RunThis.ipynb
│      Complete training + evaluation pipeline
│      Open in Google Colab — no setup needed
│
├── 🌐 app.py
│      Streamlit demo — live clinical interface
│
└── 📄 README.md
       This file
```

---

 Run in Google Colab

```
Step 1 — Go to colab.research.google.com
Step 2 — File → Upload notebook
Step 3 — Select OncoScan_Colab_RunThis.ipynb
Step 4 — Runtime → Run all
Step 5 — See full results in ~3 minutes ✅
```

---

 Roadmap

```
2025 Q1  ──●── ✅ Prototype — Module 1 complete
             │
2025 Q2  ────●── 🔨 SEER + MIMIC-IV validation
             │
2025 Q3  ────●── 🔨 Module 2 — Imaging AI
             │
2025 Q4  ────●── 📋 IRB pilot — 100 patient cohort
             │
2026 Q1  ────●── 📋 MedRxiv preprint published
             │
2026 Q2  ────●── 📋 Module 3 — Treatment Matcher
             │
2026 Q3  ────●── 📋 FDA pre-submission meeting
```

---

Seeking Collaboration

```
┌─────────────────────────────────────────────────────────┐
│                                                           │
│  🏥  Visiting researcher / research associate position   │
│      at a US academic medical centre                     │
│                                                           │
│  📋  IRB sponsorship for prospective validation          │
│                                                           │
│  💰  NIH SBIR Phase I / NCI R21 co-application          │
│                                                           │
│  🔬  Research collaboration — oncology · radiology       │
│      clinical AI · global health                         │
│                                                           │
│  📧  research@oncoscan.ai                               │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

 Data Sources Used / Planned

| Dataset | Link | What it contains |
|---------|------|-----------------|
| SEER | [seer.cancer.gov](https://seer.cancer.gov) | 50yr US cancer outcomes |
| MIMIC-IV | [physionet.org](https://physionet.org) | Real hospital clinical notes |
| TCGA | [portal.gdc.cancer.gov](https://portal.gdc.cancer.gov) | Cancer genomics + clinical |
| TCIA | [cancerimagingarchive.net](https://cancerimagingarchive.net) | Cancer imaging archive |

---

 Disclaimer

```
╔═══════════════════════════════════════════════════════════╗
║  RESEARCH PROTOTYPE ONLY                                  ║
║                                                           ║
║  Not validated for clinical use.                          ║
║  Not approved by FDA, CE, or any regulatory authority.   ║
║  Do not use for actual patient care decisions.            ║
║  Always apply clinical judgement.                         ║
╚═══════════════════════════════════════════════════════════╝
```

---

 Citation

```bibtex
@software{oncoscan2025,
  title  = {OncoScan: Integrated Clinical AI for Early Abdominal Cancer Detection},
  author = {OncoScan Research},
  year   = {2025},
  url    = {https://github.com/YOUR_USERNAME/oncoscan-research}
}
```

---

<div align="center">

*OncoScan · Clinical AI · Oncology · Global Health*
*Built by a clinician. For clinicians. For patients.*

</div>
