OncosenseAI

Clinical AI for Early Abdominal Cancer Detection

[![Status](https://img.shields.io/badge/Status-Research%20Prototype-blue?style=for-the-badge)](https://github.com/ramshazuberi81-research/oncoscan-research)
[![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Netlify-00ffaa?style=for-the-badge)](https://agent-69c270bb89e14d402--celebrated-kulfi-0a9a74.netlify.app)

> From presenting symptom to treatment protocol — in under two minutes.

[▶ Run the Live Pipeline](https://agent-69c270bb89e14d402--celebrated-kulfi-0a9a74.netlify.app)


The Problem

80%+ of abdominal cancers are diagnosed at late stage in primary care. No integrated tool exists that takes a patient from presenting symptom through to a treatment recommendation. OncosenseAI bridges that gap.

| Gastric cancer | 8.8× survival advantage with early detection |
|---|---|
| Pancreatic cancer | 3.7× survival advantage with early detection |
| Late-stage presentation | 80%+ of abdominal cancers in primary care |

 Four Integrated Modules

MODULE 01          MODULE 02          MODULE 03          MODULE 04
──────────         ──────────         ──────────         ──────────
Symptom            Visual AI          Treatment          Clinical
Intelligence       Diagnostics        Matcher            Report
Engine

17-variable        OpenCV image       NCCN/ESMO          Auto-generated
ensemble           analysis           guideline          shareable
classifier         Offline-capable    mapping +          summary
                                      genomic flags
AUROC 0.734        No cloud dep.      HER2/MSI-H/        IRB-ready
NPV 0.839          Resource-          PD-L1/KRAS         Print-
Sensitivity 0.948  limited ready      BRAF/BRCA           optimised
```

Model Performance

Validated on 500 patients from the SEER registry (pancreas n=264, stomach n=146, oesophagus n=90). Diagnosis years 2000–2022. Task: 12-month mortality prediction.

| Model | AUROC | Sensitivity | Specificity | NPV |
|---|---|---|---|---|
| Logistic Regression | 0.743 | 0.948 | 0.237 | 0.848 |
| Random Forest | 0.742 | 0.948 | 0.237 | 0.848 |
| XGBoost | 0.713 | 0.948 | 0.191 | 0.818 |
| Ensemble (Final)| 0.734 | 0.948 | 0.222 | 0.839|

> Sensitivity fixed at 0.948 — must not miss cancer patients.

 Model Results

![Model performance comparison](assets/images/model_results.png)

 SHAP Feature Importance

![SHAP feature importance](assets/images/shap_importance.png)

 Calibration Curve

![Calibration curve](assets/images/calibration.png)

Cross-Validation

![5-fold cross-validation](assets/images/cross_validation.png)

 Data Exploration — SEER Registry

![Data exploration](assets/images/data_exploration.png)

---

 Repository Structure

```
oncoscan-research/
│
├── index.html                          # Full website (GitHub Pages ready)
├── css/
│   └── style.css                       # Stylesheet
├── js/
│   └── main.js                         # Interactive symptom calculator
│
├── assets/
│   ├── images/
│   │   ├── model_results.png           # Model performance chart
│   │   ├── shap_importance.png         # SHAP feature importance
│   │   ├── calibration.png             # Calibration curve
│   │   ├── cross_validation.png        # 5-fold CV results
│   │   └── data_exploration.png        # SEER data exploration
│   ├── results.csv                     # Model metrics
│   └── features.json                   # Feature definitions (29 variables)
│
├── OncoScan_Colab_RunThis.ipynb        # Full training pipeline (run in Colab)
├── app.py                              # Streamlit demo
└── README.md
```

---

Run in Google Colab

```
1. Go to colab.research.google.com
2. File → Upload notebook
3. Select OncoScan_Colab_RunThis.ipynb
4. Runtime → Run all
5. Full results in ~3 minutes ✅
```

---

Input Features (29 Variables)

Demographics: age, sex, BMI

Alarm symptoms 🔴: rectal bleeding, unexplained weight loss, jaundice, palpable mass

Other symptoms: dysphagia, abdominal pain, change in bowel habit, early satiety, fatigue, iron deficiency anaemia, nausea/vomiting

Clinical context: symptom duration, family history of GI cancer, prior GI diagnosis

Engineered features: alarm count, many alarms flag, age over 50/60, age × alarms, age × family history, bleeding & anaemia, weight loss & jaundice, mass & weight loss, bowel & bleeding, symptoms chronic, log duration

---

 Roadmap

```
Q1 2026  ✅  All four modules complete. SEER validation (n=500).
Q2 2026  🔨  IRB pilot — 100-patient prospective cohort. MIMIC-IV NLP integration.
Q3 2026  📋  MedRxiv preprint submitted. Co-authorship opportunities open.
Q4 2026  📋  FDA 510(k) pre-submission meeting.
```

---

 Data Sources

| Dataset | Link | Contents |
|---|---|---|
| SEER | [seer.cancer.gov](https://seer.cancer.gov) | 50yr US cancer outcomes |
| MIMIC-IV | [physionet.org](https://physionet.org) | Real hospital clinical notes |
| TCGA | [portal.gdc.cancer.gov](https://portal.gdc.cancer.gov) | Cancer genomics + clinical |
| TCIA | [cancerimagingarchive.net](https://cancerimagingarchive.net) | Cancer imaging archive |

---

Seeking Collaboration

- 🏥 Visiting researcher / research associate position at a US academic medical centre
- 📋 IRB sponsorship for prospective validation (100-patient cohort)
- 💰 NIH SBIR Phase I / NCI R21 co-application
- 🔬 Research collaboration — oncology · radiology · clinical AI · global health

Contact: [ramshazubairi81@gmail.com](mailto:ramshazubairi81@gmail.com)

---

Citation

```bibtex
@software{oncosenseai2026,
  title  = {OncosenseAI: Clinical AI for Early Abdominal Cancer Detection},
  author = {Zuberi, Ramsha},
  year   = {2026},
  url    = {https://github.com/ramshazuberi81-research/oncoscan-research}
}
```

---

 Disclaimer

> RESEARCH PROTOTYPE ONLY. Not validated for clinical use. Not approved by FDA, CE, or any regulatory authority. Do not use for actual patient care decisions. Always apply clinical judgement.

---

*OncosenseAI · Built by a clinician. For clinicians. For patients.*
