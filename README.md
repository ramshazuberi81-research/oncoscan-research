



# OncosenseAI: Clinical AI Prototype for Early Abdominal Cancer Triage
> Symptom risk stratification · Image analysis · Guideline-based treatment matching · Clinical reporting

Built by a clinician-researcher. Open-source research prototype.
Ramsha Zuberi · ramshazubairi81@gmail.com · [LinkedIn](https://www.linkedin.com/in/ramsha-zuberi-26727438b/?isSelfProfile=true) · [GitHub](https://github.com/ramshazuberi81-research)

---

2. The Problem 

Abdominal cancers are often diagnosed at a late stage, partly because early symptoms such as fatigue, weight loss and abdominal pain are non-specific and are frequently attributed to benign causes in primary care. OncosenseAI explores whether structured symptom data, simple image analysis and guideline rules can help prioritise which patients should be investigated sooner.

---

## 3. Validation 

## Initial Validation on SEER Data (n=500)

> **Task:** 12-month mortality risk stratification in patients with a confirmed abdominal cancer diagnosis (pancreas n=264, stomach n=146, esophagus n=90; diagnosis years 2000-2022).
> **This is not a cancer detection result.** SEER contains only patients who already have cancer, so these metrics describe prognosis within that population. Reporting follows TRIPOD guidance; 5-fold cross-validation was used.

Keep the existing results tables (AUROC, NPV, PPV, specificity at 95% sensitivity) unchanged under this note.

---

## 4. Limitations 

## Limitations

- **Small, single-source dataset.** Validation uses a 500-case SEER sample, with no external or prospective validation yet.
- **No cancer-free comparison group.** SEER includes only cancer patients, so the current models cannot be used to estimate the probability of having cancer.
- **Imaging module is a baseline.** Module 2 uses classical OpenCV image analysis, not a trained deep learning model, and has not been validated against clinician-labelled data. A deep learning replacement is a planned next step (TCIA is a candidate data source).
- **Treatment matching is rule-based.** Module 3 encodes published guideline logic (NCCN/NICE/ESMO) and has not been clinically evaluated.
- **Not for clinical use.** This is a research prototype; see the disclaimer below.

---



## Roadmap

- Done: Module 1, symptom risk model with initial SEER validation (AUROC 0.790)
- Done: Module 2 (OpenCV baseline), Module 3 (guideline-based treatment matcher), Module 4 (PDF report generator)
- Planned: Replace the OpenCV imaging module with a deep learning model on public imaging data
- Planned: External validation on an independent dataset (MIMIC-IV access in progress)
- Planned: Preprint (medRxiv)
- Future, subject to partnerships and ethics approval: Prospective pilot study

---

## 6. Seeking Collaboration 

## Open to Collaboration

| Area | What I'm looking for |
| --- | --- |
| Deep learning / medical imaging | Help replacing the baseline imaging module and benchmarking it properly |
| External validation | Access to independent datasets or clinical partners |
| Ethics and prospective study | Institutional partners for an IRB-approved pilot |
| Funding | Co-applications and grant-writing collaboration |
| Visiting research | Visiting researcher or research associate positions |

---


- [ ] Replace every `#` placeholder link (LinkedIn, GitHub, Live Demo) with a real URL
- [ ] Remove the duplicate `Readme.md.html` if it is not needed
