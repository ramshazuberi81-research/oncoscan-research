"""
OncosenseAI — Module 5: Genomic Risk & Pharmacogenomics Engine
==============================================================
Author : Ramsha Zuberi, Phyisician 
Affil. : Independent Physician-Researcher
Contact : ramshazuberi81@gmail.com
GitHub : github.com/ramshazuberi81-research/oncoscan-research

Description
-----------
Genomic risk stratification and pharmacogenomic profiling for early
detection of abdominal cancers (pancreatic, gastric, esophageal).

Updates in this version
-----------------------
- AMP/ASCO/CAP 2017 variant classification tiers (I–IV) integrated
  into all variant database entries and VariantResult output
- CHAS comorbidity scoring (Coronary heart disease, Hypertension,
  Age ≥65, Stroke/TIA, Diabetes, CKD, H. pylori, IBD) as a
  multiplicative risk modifier replacing simple demographic stacking
- CHASProfile dataclass for structured comorbidity input
- CancerRiskScore now exposes chas_modifier and amp_tier fields
- parse_report_text upgraded with pharmacogenomic variant detection

SEER Validation Context
-----------------------
OncosenseAI ensemble model: AUROC 0.753
Logistic regression model:  AUROC 0.790
NPV at 95% sensitivity:     0.853
Cohort: n=500 SEER records
Cancer types: Pancreatic, Gastric, Esophageal

References
----------
[1] Goggins M et al. Gut. 2020;69(1):7-17.
[2] van der Post RS et al. J Med Genet. 2015;52(6):361-374.
[3] Domchek SM et al. JAMA. 2010.
[4] Hampel H et al. GeneReviews. NCBI Bookshelf. 2021.
[5] Syngal S et al. Am J Gastroenterol. 2015.
[6] PharmGKB. pharmgkb.org
[7] CPIC Guidelines. cpicpgx.org
[8] Li MM et al. AMP/ASCO/CAP guidelines. J Mol Diagn. 2017.
[9] Lip GY et al. CHAS/CHA2DS2-VASc. Chest. 2010.

License: MIT — Research use only. Not for clinical deployment.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────────
# ENUMERATIONS
# ─────────────────────────────────────────────

class RiskTier(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    ROUTINE  = "ROUTINE"


class UrgencyAction(str, Enum):
    ONCOLOGY_2WK   = "Refer to oncology within 2 weeks"
    IMAGING_PANEL  = "Arrange contrast CT + CA19-9/CEA panel within 4 weeks"
    FOLLOWUP_3MO   = "3-month follow-up with repeat symptom review"
    ANNUAL_SCREEN  = "Annual surveillance recommended"


class CancerType(str, Enum):
    PANCREATIC  = "pancreatic"
    GASTRIC     = "gastric"
    ESOPHAGEAL  = "esophageal"
    BREAST      = "breast"
    COLORECTAL  = "colorectal"
    OVARIAN     = "ovarian"
    MELANOMA    = "melanoma"


class MetaboliserStatus(str, Enum):
    POOR        = "Poor Metaboliser"
    INTERMEDIATE = "Intermediate Metaboliser"
    NORMAL      = "Normal Metaboliser"
    RAPID       = "Rapid Metaboliser"
    ULTRARAPID  = "Ultra-rapid Metaboliser"


class AMPTier(str, Enum):
    """
    AMP/ASCO/CAP 2017 Variant Classification Tiers [8]
    Tier I   : Variants of strong clinical significance
    Tier II  : Variants of potential clinical significance
    Tier III : Variants of unknown clinical significance (VUS)
    Tier IV  : Benign or likely benign variants
    """
    TIER_I   = "I"    # Strong oncogenic / tumour suppressor evidence
    TIER_II  = "II"   # Likely pathogenic / potential significance
    TIER_III = "III"  # Variant of uncertain significance (VUS)
    TIER_IV  = "IV"   # Likely benign


# ─────────────────────────────────────────────
# VARIANT DATABASE
# AMP/ASCO/CAP tiers assigned per published evidence [1-5,8]
# ─────────────────────────────────────────────

VARIANT_DATABASE: dict[str, dict] = {
    "BRCA1": {
        "gene_full": "Breast Cancer Gene 1",
        "mechanism": "Homologous recombination DNA repair pathway",
        "associated_cancers": [CancerType.BREAST, CancerType.OVARIAN, CancerType.PANCREATIC],
        "risk_multipliers": {
            CancerType.BREAST:      5.0,
            CancerType.OVARIAN:    10.0,
            CancerType.PANCREATIC:  2.4,
        },
        "population_frequency": 0.001,
        "inheritance": "Autosomal dominant",
        # AMP/ASCO/CAP: Tier I — strong clinical significance; well-validated pathogenic variant
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Well-validated pathogenic variant with established penetrance data. "
            "Meets AMP/ASCO/CAP Tier I criteria: recurrently mutated, functional studies "
            "demonstrate loss of function, included in multiple clinical guidelines (NCCN HBOC)."
        ),
        "targeted_agents": ["Olaparib", "Niraparib"],
        "clinical_note": "Surveillance per NCCN HBOC guidelines. Consider risk-reducing surgery.",
        "reference": "NCCN v2.2024 Hereditary Breast/Ovarian Cancer",
    },

    "BRCA2": {
        "gene_full": "Breast Cancer Gene 2",
        "mechanism": "Homologous recombination DNA repair pathway",
        "associated_cancers": [CancerType.PANCREATIC, CancerType.GASTRIC, CancerType.BREAST],
        "risk_multipliers": {
            CancerType.PANCREATIC: 3.8,
            CancerType.GASTRIC:    2.6,
            CancerType.BREAST:     4.5,
        },
        "population_frequency": 0.002,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Tier I: Pathogenic BRCA2 variants are among the most validated cancer-predisposition "
            "variants. Goggins et al. 2020 [1] specifically supports pancreatic surveillance. "
            "Functional data, population studies, and clinical trial evidence meet all Tier I criteria."
        ),
        "targeted_agents": ["Olaparib", "Rucaparib"],
        "clinical_note": "Annual pancreatic EUS/MRI from age 50 or 10yr before earliest affected relative.",
        "reference": "Goggins M et al. Gut. 2020 [1]",
    },

    "TP53": {
        "gene_full": "Tumour Protein 53 (Li-Fraumeni Syndrome)",
        "mechanism": "Master tumour suppressor — cell cycle arrest, apoptosis",
        "associated_cancers": [CancerType.GASTRIC, CancerType.ESOPHAGEAL, CancerType.PANCREATIC],
        "risk_multipliers": {
            CancerType.GASTRIC:    4.1,
            CancerType.ESOPHAGEAL: 3.5,
            CancerType.PANCREATIC: 3.0,
        },
        "population_frequency": 0.0003,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Tier I: Germline TP53 pathogenic variants define Li-Fraumeni syndrome. "
            "Extensive functional, segregation, and population data. NCCN and Kratz et al. 2017 "
            "support clinical actionability."
        ),
        "targeted_agents": [],
        "clinical_note": "Li-Fraumeni syndrome. Whole-body MRI surveillance recommended annually.",
        "reference": "Kratz CP et al. J Clin Oncol. 2017",
    },

    "KRAS": {
        "gene_full": "Kirsten Rat Sarcoma Viral Proto-oncogene",
        "mechanism": "RAS/MAPK oncogenic signalling — constitutive activation",
        "associated_cancers": [CancerType.PANCREATIC, CancerType.COLORECTAL, CancerType.GASTRIC],
        "risk_multipliers": {
            CancerType.PANCREATIC: 5.2,
            CancerType.COLORECTAL: 2.5,
            CancerType.GASTRIC:    2.0,
        },
        "population_frequency": 0.0001,
        "inheritance": "Somatic (predominantly); germline rare (RASopathy)",
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Tier I: KRAS G12C/D/V are recurrently activated somatic oncogenic drivers "
            "in pancreatic ductal adenocarcinoma (>90%). Sotorasib / Adagrasib approved for "
            "KRAS G12C targets. Moore et al. 2020 confirms strong clinical significance."
        ),
        "targeted_agents": ["Erlotinib", "Sotorasib", "Adagrasib"],
        "clinical_note": "Germline KRAS: Noonan-like syndrome. Somatic: standard PDAC treatment pathway.",
        "reference": "Moore AR et al. Nat Rev Cancer. 2020",
    },

    "CDH1": {
        "gene_full": "E-cadherin (Hereditary Diffuse Gastric Cancer)",
        "mechanism": "Cell adhesion molecule — loss enables epithelial-mesenchymal transition",
        "associated_cancers": [CancerType.GASTRIC, CancerType.BREAST],
        "risk_multipliers": {
            CancerType.GASTRIC: 6.8,
            CancerType.BREAST:  2.5,
        },
        "population_frequency": 0.0001,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Tier I: Pathogenic CDH1 variants define HDGC syndrome with 67–70% lifetime gastric "
            "cancer risk. van der Post RS et al. 2015 [2] provides the definitive clinical guideline. "
            "Prophylactic total gastrectomy is a clinical standard."
        ),
        "targeted_agents": [],
        "clinical_note": "Prophylactic total gastrectomy discussion indicated. HDGC clinic referral.",
        "reference": "van der Post RS et al. J Med Genet. 2015 [2]",
    },

    "CDKN2A": {
        "gene_full": "Cyclin-Dependent Kinase Inhibitor 2A (p16/p14ARF)",
        "mechanism": "Cell cycle regulation — G1/S checkpoint control",
        "associated_cancers": [CancerType.PANCREATIC, CancerType.MELANOMA],
        "risk_multipliers": {
            CancerType.PANCREATIC: 2.9,
            CancerType.MELANOMA:   5.0,
        },
        "population_frequency": 0.0004,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_II,
        "amp_rationale": (
            "Tier II: Likely pathogenic. FAMM syndrome variants have well-described melanoma risk. "
            "Pancreatic risk is supported by Vasen et al. 2016 but penetrance ranges vary widely "
            "by variant and family context — meets Tier II (potential clinical significance)."
        ),
        "targeted_agents": [],
        "clinical_note": "Annual pancreatic MRI/EUS from age 40. Annual dermatological surveillance.",
        "reference": "Vasen HF et al. Gut. 2016",
    },

    "MLH1": {
        "gene_full": "MutL Homolog 1 (Lynch Syndrome)",
        "mechanism": "Mismatch repair (MMR) gene — microsatellite instability pathway",
        "associated_cancers": [CancerType.GASTRIC, CancerType.COLORECTAL, CancerType.ESOPHAGEAL],
        "risk_multipliers": {
            CancerType.GASTRIC:     2.7,
            CancerType.COLORECTAL:  5.0,
            CancerType.ESOPHAGEAL:  2.0,
        },
        "population_frequency": 0.0003,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Tier I: MLH1 pathogenic variants are causal for Lynch syndrome. Hampel et al. [4] "
            "and ACG guidelines [5] confirm clinical significance. Pembrolizumab approved for "
            "MSI-H/dMMR tumours irrespective of origin."
        ),
        "targeted_agents": ["Pembrolizumab"],
        "clinical_note": "Lynch syndrome. Annual colonoscopy from age 25. Upper GI surveillance.",
        "reference": "Hampel H et al. GeneReviews. 2021 [4]",
    },

    "MSH2": {
        "gene_full": "MutS Homolog 2 (Lynch Syndrome)",
        "mechanism": "Mismatch repair (MMR) — MSH2-MSH6 heterodimer formation",
        "associated_cancers": [CancerType.GASTRIC, CancerType.COLORECTAL, CancerType.ESOPHAGEAL],
        "risk_multipliers": {
            CancerType.GASTRIC:     2.5,
            CancerType.COLORECTAL:  4.5,
            CancerType.ESOPHAGEAL:  1.9,
        },
        "population_frequency": 0.0003,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_I,
        "amp_rationale": (
            "Tier I: MSH2 pathogenic variants are a causal Lynch syndrome gene. Similar evidence "
            "base to MLH1. MSH2 deletion is clinically actionable per Syngal et al. 2015 [5]."
        ),
        "targeted_agents": ["Pembrolizumab"],
        "clinical_note": "Lynch syndrome variant. Similar surveillance to MLH1. MSH2 deletion testing.",
        "reference": "Syngal S et al. Am J Gastroenterol. 2015 [5]",
    },

    "NOTCH1": {
        "gene_full": "Neurogenic locus notch homolog protein 1",
        "mechanism": "Notch signalling — cell fate, differentiation, tumour suppression",
        "associated_cancers": [CancerType.ESOPHAGEAL, CancerType.GASTRIC],
        "risk_multipliers": {
            CancerType.ESOPHAGEAL: 2.3,
            CancerType.GASTRIC:    1.8,
        },
        "population_frequency": 0.0005,
        "inheritance": "Autosomal dominant (loss of function)",
        "amp_tier": AMPTier.TIER_II,
        "amp_rationale": (
            "Tier II: NOTCH1 LoF variants are emerging biomarkers in esophageal SCC (Agrawal et al. "
            "2012). Penetrance data is limited; variant interpretation requires functional context. "
            "Meets Tier II — potential clinical significance."
        ),
        "targeted_agents": [],
        "clinical_note": "Emerging evidence in esophageal SCC. Endoscopic surveillance yearly.",
        "reference": "Agrawal N et al. Science. 2012",
    },

    "SMAD4": {
        "gene_full": "SMAD Family Member 4 (Juvenile Polyposis Syndrome)",
        "mechanism": "TGF-β signalling pathway — tumour suppressor",
        "associated_cancers": [CancerType.PANCREATIC, CancerType.GASTRIC],
        "risk_multipliers": {
            CancerType.PANCREATIC: 2.8,
            CancerType.GASTRIC:    2.2,
        },
        "population_frequency": 0.0002,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_II,
        "amp_rationale": (
            "Tier II: SMAD4 pathogenic variants cause juvenile polyposis syndrome with elevated "
            "GI cancer risk. Brosens et al. 2011 supports actionability. Penetrance data is "
            "moderate — Tier II appropriate."
        ),
        "targeted_agents": [],
        "clinical_note": "Juvenile polyposis syndrome. Upper and lower GI endoscopy from age 15.",
        "reference": "Brosens LA et al. Gut. 2011",
    },

    "ATM": {
        "gene_full": "Ataxia Telangiectasia Mutated",
        "mechanism": "DNA double-strand break repair — checkpoint kinase",
        "associated_cancers": [CancerType.PANCREATIC, CancerType.GASTRIC, CancerType.BREAST],
        "risk_multipliers": {
            CancerType.PANCREATIC: 2.4,
            CancerType.GASTRIC:    1.9,
            CancerType.BREAST:     2.5,
        },
        "population_frequency": 0.003,
        "inheritance": "Autosomal dominant (heterozygous risk); autosomal recessive (A-T)",
        "amp_tier": AMPTier.TIER_II,
        "amp_rationale": (
            "Tier II: Heterozygous ATM pathogenic variants confer moderate cancer risk "
            "(Thompson et al. 2005). Evidence supports potential clinical significance but "
            "penetrance is more variable than BRCA1/2 — Tier II classification is appropriate. "
            "PARP inhibitor sensitivity supports Olaparib use."
        ),
        "targeted_agents": ["Olaparib"],
        "clinical_note": "Moderate risk. Cascade testing recommended. PARP inhibitor sensitivity.",
        "reference": "Thompson D et al. Am J Hum Genet. 2005",
    },

    "PALB2": {
        "gene_full": "Partner and Localizer of BRCA2",
        "mechanism": "BRCA1-BRCA2 bridge protein — homologous recombination",
        "associated_cancers": [CancerType.PANCREATIC, CancerType.BREAST],
        "risk_multipliers": {
            CancerType.PANCREATIC: 3.1,
            CancerType.BREAST:     3.4,
        },
        "population_frequency": 0.001,
        "inheritance": "Autosomal dominant",
        "amp_tier": AMPTier.TIER_II,
        "amp_rationale": (
            "Tier II: PALB2 pathogenic variants confer substantial breast and pancreatic risk "
            "(Antoniou et al. 2014). Risk approaches BRCA2 level for pancreatic cancer. "
            "Emerging clinical guideline inclusion — currently Tier II, trending toward Tier I."
        ),
        "targeted_agents": ["Olaparib"],
        "clinical_note": "Annual pancreatic EUS/MRI from age 50. Risk approaches BRCA2 level.",
        "reference": "Antoniou AC et al. N Engl J Med. 2014",
    },
}


# ─────────────────────────────────────────────
# PHARMACOGENOMICS DATABASE
# ─────────────────────────────────────────────

PHARMACOGENOMICS_DATABASE: dict[str, dict] = {
    "CYP2D6": {
        "enzyme_full": "Cytochrome P450 2D6",
        "affected_drugs": ["Tamoxifen", "Codeine", "Tramadol", "Ondansetron", "Metoclopramide"],
        "poor_metaboliser_variants":    ["CYP2D6*3", "CYP2D6*4", "CYP2D6*5", "CYP2D6*6"],
        "ultrarapid_metaboliser_variants": ["CYP2D6*1xN", "CYP2D6*2xN"],
        "clinical_relevance_oncology": "HIGH",
        "clinical_note": (
            "CYP2D6 poor metabolisers on Tamoxifen have significantly reduced endoxifen levels, "
            "potentially compromising efficacy. Consider alternative endocrine therapy or dose "
            "adjustment. Ultra-rapid metabolisers on Codeine/Tramadol face toxicity risk."
        ),
        "cpic_guideline": "CPIC Tamoxifen Guideline (2018, updated 2021)",
    },
    "CYP3A4": {
        "enzyme_full": "Cytochrome P450 3A4",
        "affected_drugs": ["Irinotecan", "Docetaxel", "Paclitaxel", "Erlotinib", "Sunitinib", "Midazolam"],
        "poor_metaboliser_variants":    ["CYP3A4*20", "CYP3A4*22"],
        "ultrarapid_metaboliser_variants": [],
        "clinical_relevance_oncology": "HIGH",
        "clinical_note": (
            "CYP3A4 variants affect metabolism of multiple first-line GI oncology drugs. "
            "Drug-drug interactions via CYP3A4 inhibition (azole antifungals, macrolides) "
            "common in oncology settings. Screen for comedications."
        ),
        "cpic_guideline": "CPIC Codeine/Opioid Guideline; NCI Drug Interaction Program",
    },
    "CYP2C9": {
        "enzyme_full": "Cytochrome P450 2C9",
        "affected_drugs": ["Celecoxib", "Warfarin", "NSAIDs (general)", "Siponimod"],
        "poor_metaboliser_variants":    ["CYP2C9*2", "CYP2C9*3", "CYP2C9*5", "CYP2C9*6"],
        "ultrarapid_metaboliser_variants": [],
        "clinical_relevance_oncology": "MODERATE",
        "clinical_note": (
            "CYP2C9 poor metabolisers on Warfarin require significantly lower doses. "
            "Relevant in oncology for DVT prophylaxis."
        ),
        "cpic_guideline": "CPIC Warfarin Guideline (2017)",
    },
    "DPYD": {
        "enzyme_full": "Dihydropyrimidine Dehydrogenase",
        "affected_drugs": ["5-Fluorouracil (5-FU)", "Capecitabine", "Tegafur"],
        "poor_metaboliser_variants":    ["DPYD*2A", "DPYD*13", "c.2846A>T", "HapB3"],
        "ultrarapid_metaboliser_variants": [],
        "clinical_relevance_oncology": "CRITICAL",
        "clinical_note": (
            "DPYD deficiency causes severe, potentially fatal 5-FU toxicity. "
            "DPYD*2A carriers: reduce 5-FU / Capecitabine dose by 50% minimum. "
            "HIGHLY RELEVANT for gastric and esophageal cancer regimens (FLOT, FOLFOX, ECF). "
            "Pre-treatment DPYD testing now recommended in EU guidelines."
        ),
        "cpic_guideline": "CPIC Fluoropyrimidine Guideline (2017, updated 2023)",
    },
    "UGT1A1": {
        "enzyme_full": "UDP-Glucuronosyltransferase 1A1",
        "affected_drugs": ["Irinotecan", "Belinostat"],
        "poor_metaboliser_variants":    ["UGT1A1*28", "UGT1A1*6"],
        "ultrarapid_metaboliser_variants": [],
        "clinical_relevance_oncology": "HIGH",
        "clinical_note": (
            "UGT1A1*28 homozygotes have ~50% reduced Irinotecan clearance. "
            "Risk of severe neutropenia and diarrhoea at standard doses. "
            "Consider 25–30% dose reduction for *28/*28 genotype. "
            "Relevant for FOLFIRINOX regimens in pancreatic cancer."
        ),
        "cpic_guideline": "CPIC Irinotecan/UGT1A1 Guideline (2015, updated 2022)",
    },
    "TPMT": {
        "enzyme_full": "Thiopurine S-Methyltransferase",
        "affected_drugs": ["Azathioprine", "6-Mercaptopurine", "Thioguanine"],
        "poor_metaboliser_variants":    ["TPMT*2", "TPMT*3A", "TPMT*3B", "TPMT*3C"],
        "ultrarapid_metaboliser_variants": [],
        "clinical_relevance_oncology": "MODERATE",
        "clinical_note": (
            "TPMT poor metabolisers on thiopurines face severe myelosuppression. "
            "Primarily relevant in IBD-associated GI malignancy and post-transplant oncology."
        ),
        "cpic_guideline": "CPIC Thiopurine Guideline (2013, updated 2018)",
    },
}


# ─────────────────────────────────────────────
# DEMOGRAPHIC MODIFIERS
# ─────────────────────────────────────────────

AGE_MODIFIERS: dict[str, float] = {
    "< 30":  0.85,
    "30-40": 0.95,
    "41-50": 1.10,
    "51-60": 1.25,
    "61-70": 1.40,
    "> 70":  1.50,
}

FAMILY_HISTORY_MODIFIERS: dict[str, float] = {
    "None":                    1.00,
    "First-degree":            1.30,
    "Multiple relatives":      1.55,
    "Known hereditary syndrome": 1.80,
}

CANCER_BASELINE_RISK: dict[CancerType, float] = {
    CancerType.PANCREATIC:  0.013,
    CancerType.GASTRIC:     0.017,
    CancerType.ESOPHAGEAL:  0.009,
    CancerType.BREAST:      0.125,
    CancerType.COLORECTAL:  0.042,
    CancerType.OVARIAN:     0.013,
    CancerType.MELANOMA:    0.022,
}

SYMPTOM_WEIGHTS: dict[str, dict] = {
    "abdominal_pain": {"weight": 0.70, "cancers": [CancerType.PANCREATIC, CancerType.GASTRIC]},
    "weight_loss":    {"weight": 0.90, "cancers": [CancerType.PANCREATIC, CancerType.GASTRIC, CancerType.ESOPHAGEAL]},
    "dysphagia":      {"weight": 0.85, "cancers": [CancerType.ESOPHAGEAL, CancerType.GASTRIC]},
    "jaundice":       {"weight": 0.95, "cancers": [CancerType.PANCREATIC]},
    "nausea":         {"weight": 0.60, "cancers": [CancerType.GASTRIC, CancerType.PANCREATIC]},
    "dark_stool":     {"weight": 0.80, "cancers": [CancerType.GASTRIC, CancerType.ESOPHAGEAL]},
    "fatigue":        {"weight": 0.55, "cancers": [CancerType.PANCREATIC, CancerType.GASTRIC]},
    "early_satiety":  {"weight": 0.65, "cancers": [CancerType.GASTRIC]},
    "heartburn":      {"weight": 0.50, "cancers": [CancerType.ESOPHAGEAL]},
    "back_pain":      {"weight": 0.75, "cancers": [CancerType.PANCREATIC]},
}


# ─────────────────────────────────────────────
# CHAS COMORBIDITY SCORING
# Adapted for GI oncology from CHA2DS2-VASc [9]
# ─────────────────────────────────────────────

CHAS_ITEMS: dict[str, dict] = {
    "coronary_heart_disease": {
        "score": 1,
        "label": "Coronary heart disease",
        "rationale": "Cardiovascular comorbidity increases surgical risk and modifies cancer trajectory.",
    },
    "hypertension": {
        "score": 1,
        "label": "Hypertension",
        "rationale": "HTN associated with increased gastric and esophageal cancer risk via chronic inflammation.",
    },
    "age_gte_65": {
        "score": 1,
        "label": "Age ≥ 65",
        "rationale": "Age is an independent cancer risk modifier; applied as CHAS item when not captured in age_group.",
    },
    "stroke_or_tia": {
        "score": 2,
        "label": "Stroke / TIA",
        "rationale": "Weighted ×2: reflects shared inflammatory/vascular pathways and higher overall disease burden.",
    },
    "diabetes_mellitus": {
        "score": 1,
        "label": "Diabetes mellitus",
        "rationale": "DM is an independent risk factor for pancreatic cancer; modifies treatment tolerance.",
    },
    "ckd_renal_impairment": {
        "score": 1,
        "label": "CKD / renal impairment",
        "rationale": "Affects drug clearance (Capecitabine, Carboplatin dosing) and surgical fitness.",
    },
    "h_pylori": {
        "score": 1,
        "label": "H. pylori positive",
        "rationale": "WHO Group I carcinogen for gastric cancer; applies a 1.25× gastric risk multiplier.",
    },
    "ibd_chronic_gi_inflammation": {
        "score": 1,
        "label": "IBD / chronic GI inflammation",
        "rationale": "Colitis-associated colorectal and gastric cancer risk; thiopurine TPMT relevance.",
    },
}

CHAS_RISK_MODIFIERS: dict[tuple, float] = {
    # (min_score, max_score): modifier
    (0, 1):  1.00,  # No meaningful comorbidity burden
    (2, 3):  1.15,  # Moderate comorbidity
    (4, 5):  1.30,  # High comorbidity
    (6, 99): 1.45,  # Very high comorbidity
}

def compute_chas_modifier(chas_score: int) -> float:
    """Return the multiplicative risk modifier for a given CHAS score."""
    for (lo, hi), mod in CHAS_RISK_MODIFIERS.items():
        if lo <= chas_score <= hi:
            return mod
    return 1.0

def interpret_chas(score: int) -> str:
    if score == 0:
        return "No comorbidity burden — standard risk modifier"
    elif score <= 1:
        return "Low comorbidity — standard risk modifier (1.00×)"
    elif score <= 3:
        return "Moderate comorbidity — 1.15× risk adjustment"
    elif score <= 5:
        return "High comorbidity — 1.30× risk adjustment"
    else:
        return "Very high comorbidity — 1.45× risk adjustment"


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class PatientProfile:
    """Input patient demographics and risk modifiers."""
    age_group:      str              # "< 30" | "30-40" | "41-50" | "51-60" | "61-70" | "> 70"
    sex:            str              # "Female" | "Male" | "Other"
    family_history: str              # "None" | "First-degree" | "Multiple relatives" | "Known hereditary syndrome"
    smoking:        bool = False
    alcohol:        bool = False
    bmi_obese:      bool = False     # BMI > 30
    h_pylori:       bool = False     # H. pylori history (also counted in CHAS if positive)


@dataclass
class CHASProfile:
    """
    CHAS comorbidity profile for GI oncology risk modification.
    Each boolean maps to a scored item in CHAS_ITEMS.
    """
    coronary_heart_disease:     bool = False
    hypertension:               bool = False
    age_gte_65:                 bool = False
    stroke_or_tia:              bool = False
    diabetes_mellitus:          bool = False
    ckd_renal_impairment:       bool = False
    h_pylori:                   bool = False  # Cross-referenced with PatientProfile
    ibd_chronic_gi_inflammation: bool = False

    def score(self) -> int:
        """Compute total CHAS score."""
        total = 0
        if self.coronary_heart_disease:      total += 1
        if self.hypertension:                total += 1
        if self.age_gte_65:                  total += 1
        if self.stroke_or_tia:               total += 2  # Weighted ×2
        if self.diabetes_mellitus:           total += 1
        if self.ckd_renal_impairment:        total += 1
        if self.h_pylori:                    total += 1
        if self.ibd_chronic_gi_inflammation: total += 1
        return total

    def modifier(self) -> float:
        """Return the multiplicative risk modifier for this CHAS score."""
        return compute_chas_modifier(self.score())

    def interpretation(self) -> str:
        return interpret_chas(self.score())

    def active_items(self) -> list[str]:
        """Return human-readable list of active comorbidities."""
        items = []
        field_map = {
            "coronary_heart_disease": "Coronary heart disease",
            "hypertension": "Hypertension",
            "age_gte_65": "Age ≥ 65",
            "stroke_or_tia": "Stroke / TIA (×2)",
            "diabetes_mellitus": "Diabetes mellitus",
            "ckd_renal_impairment": "CKD / renal impairment",
            "h_pylori": "H. pylori positive",
            "ibd_chronic_gi_inflammation": "IBD / chronic GI inflammation",
        }
        for attr, label in field_map.items():
            if getattr(self, attr):
                items.append(label)
        return items


@dataclass
class VariantResult:
    """Risk contribution from a single genomic variant — includes AMP/ASCO/CAP tier."""
    variant:      str
    gene_full:    str
    mechanism:    str
    inheritance:  str
    amp_tier:     str       # AMPTier value: "I" | "II" | "III" | "IV"
    amp_rationale: str
    targeted_agents: list[str]
    cancer_risks: dict[str, float]   # CancerType -> risk multiplier
    clinical_note: str
    reference:    str


@dataclass
class PharmacoFlag:
    """Pharmacogenomic flag for a single enzyme."""
    enzyme:             str
    enzyme_full:        str
    affected_drugs:     list[str]
    clinical_relevance: str
    clinical_note:      str
    cpic_guideline:     str


@dataclass
class CancerRiskScore:
    """Risk score for a single cancer type — now exposes CHAS modifier."""
    cancer_type:          str
    raw_score:            float
    normalised_score:     float
    genomic_contribution: float
    symptom_contribution: float
    demographic_modifier: float
    chas_modifier:        float   # NEW: CHAS component of demographic_modifier
    driving_variants:     list[str]
    amp_tiers:            list[str]  # NEW: AMP tiers of driving variants


@dataclass
class CHASResult:
    """Structured CHAS output included in the RiskReport."""
    score:          int
    modifier:       float
    interpretation: str
    active_items:   list[str]


@dataclass
class RiskReport:
    """Full genomic risk assessment output."""
    timestamp:               str
    patient_profile:         PatientProfile
    chas_result:             CHASResult        # NEW
    variants_assessed:       list[str]
    variant_results:         list[VariantResult]
    pharma_flags:            list[PharmacoFlag]
    cancer_scores:           list[CancerRiskScore]
    composite_score:         float
    genomic_score:           float
    risk_tier:               RiskTier
    urgency_action:          str
    clinical_recommendations: list[str]
    disclaimer:              str


# ─────────────────────────────────────────────
# CORE ENGINE
# ─────────────────────────────────────────────

class GenomicRiskEngine:
    """
    Multimodal genomic risk engine for OncosenseAI Module 5.

    Computes cancer-specific risk scores by integrating:
      1. Pathogenic variant burden (12 variants, AMP/ASCO/CAP classified)
      2. Symptom contributions (NICE NG12 alarm feature weighting)
      3. Demographic modifiers (age, sex, family history, lifestyle)
      4. CHAS comorbidity scoring (8-item GI-oncology adapted profile)
      5. Pharmacogenomic profiling (6 CYP/metaboliser enzymes, CPIC)

    Output: structured RiskReport with AMP tiers, CHAS modifier,
    pharmacogenomic flags, and prioritised clinical recommendations.
    """

    DISCLAIMER = (
        "RESEARCH PROTOTYPE ONLY. Not validated for clinical use. "
        "Not approved by FDA, CE, MHRA, or any regulatory authority. "
        "Do not use for actual patient care decisions. "
        "OncosenseAI — IRB exempt under 45 CFR 46 (SEER retrospective analysis). "
        "Genomic risk multipliers sourced from published penetrance literature — "
        "not derived from the SEER validation cohort. "
        "AMP/ASCO/CAP tiers are research assignments; validate with certified molecular pathologist."
    )

    def __init__(self):
        self.variant_db = VARIANT_DATABASE
        self.pharma_db  = PHARMACOGENOMICS_DATABASE

    # ── PUBLIC API ──────────────────────────────

    def assess(
        self,
        patient:         PatientProfile,
        variants:        list[str],
        symptoms:        list[str] | None = None,
        pharma_variants: dict[str, list[str]] | None = None,
        chas:            CHASProfile | None = None,
    ) -> RiskReport:
        """
        Run a full genomic risk assessment.

        Parameters
        ----------
        patient         : PatientProfile with demographic details
        variants        : List of pathogenic variant names (e.g. ["BRCA2", "CDH1"])
        symptoms        : List of symptom IDs from SYMPTOM_WEIGHTS keys
        pharma_variants : Dict mapping enzyme name to detected variants
                          e.g. {"DPYD": ["DPYD*2A"], "CYP2D6": ["CYP2D6*4"]}
        chas            : CHASProfile comorbidity input (optional; h_pylori synced from patient)

        Returns
        -------
        RiskReport with full assessment including AMP tiers, CHAS modifier, recommendations
        """
        symptoms        = symptoms or []
        pharma_variants = pharma_variants or {}
        chas            = chas or CHASProfile()

        # Sync h_pylori between PatientProfile and CHASProfile
        if patient.h_pylori:
            chas.h_pylori = True

        # Validate inputs
        valid_variants = [v for v in variants if v in self.variant_db]
        invalid = set(variants) - set(valid_variants)
        if invalid:
            print(f"[WARNING] Unrecognised variants skipped: {invalid}")

        # Step 1: CHAS result
        chas_result = CHASResult(
            score          = chas.score(),
            modifier       = chas.modifier(),
            interpretation = chas.interpretation(),
            active_items   = chas.active_items(),
        )

        # Step 2: Per-cancer risk scores
        cancer_scores = self._compute_cancer_scores(patient, valid_variants, symptoms, chas)

        # Step 3: Composite score
        composite, genomic = self._compute_composite(cancer_scores, valid_variants)

        # Step 4: Risk tier
        tier, urgency = self._classify_risk(composite, cancer_scores)

        # Step 5: Variant results (with AMP tiers)
        variant_results = self._build_variant_results(valid_variants)

        # Step 6: Pharmacogenomic flags
        pharma_flags = self._build_pharma_flags(pharma_variants, valid_variants)

        # Step 7: Clinical recommendations
        recommendations = self._generate_recommendations(
            composite, cancer_scores, valid_variants, pharma_flags, patient, chas_result
        )

        return RiskReport(
            timestamp               = datetime.utcnow().isoformat() + "Z",
            patient_profile         = patient,
            chas_result             = chas_result,
            variants_assessed       = valid_variants,
            variant_results         = variant_results,
            pharma_flags            = pharma_flags,
            cancer_scores           = cancer_scores,
            composite_score         = round(composite, 2),
            genomic_score           = round(genomic, 2),
            risk_tier               = tier,
            urgency_action          = urgency,
            clinical_recommendations = recommendations,
            disclaimer              = self.DISCLAIMER,
        )

    def parse_report_text(self, text: str) -> dict:
        """
        Auto-detect variant names AND pharmacogenomic variants from raw genetic report text.
        Supports 23andMe, AncestryDNA, and VCF-format exports.

        Returns
        -------
        dict with:
            detected_variants     : list of genomic variant names found
            detected_pharma       : dict mapping enzyme to detected variants
            amp_tiers             : dict mapping variant to its AMP tier
        """
        text_upper = text.upper()
        detected = []
        amp_tiers = {}

        for variant_name, vdata in self.variant_db.items():
            if variant_name.upper() in text_upper:
                detected.append(variant_name)
                amp_tiers[variant_name] = vdata["amp_tier"].value

        # Detect pharmacogenomic variants
        detected_pharma: dict[str, list[str]] = {}
        for enzyme, pdata in self.pharma_db.items():
            found = []
            for pv in pdata["poor_metaboliser_variants"] + pdata.get("ultrarapid_metaboliser_variants", []):
                if pv.upper() in text_upper:
                    found.append(pv)
            if found:
                detected_pharma[enzyme] = found

        return {
            "detected_variants":  detected,
            "detected_pharma":    detected_pharma,
            "amp_tiers":          amp_tiers,
            "variant_count":      len(detected),
            "pharma_enzyme_count": len(detected_pharma),
        }

    def get_variant_info(self, variant: str) -> dict | None:
        return self.variant_db.get(variant)

    def get_pharma_info(self, enzyme: str) -> dict | None:
        return self.pharma_db.get(enzyme)

    def report_to_dict(self, report: RiskReport) -> dict:
        """Serialise RiskReport to JSON-safe dict."""
        d = asdict(report)
        d["risk_tier"]      = report.risk_tier.value
        d["patient_profile"] = asdict(report.patient_profile)
        d["chas_result"]    = asdict(report.chas_result)
        return d

    def report_to_json(self, report: RiskReport, indent: int = 2) -> str:
        return json.dumps(self.report_to_dict(report), indent=indent, default=str)

    # ── INTERNAL COMPUTATION ─────────────────────

    def _compute_cancer_scores(
        self,
        patient:  PatientProfile,
        variants: list[str],
        symptoms: list[str],
        chas:     CHASProfile,
    ) -> list[CancerRiskScore]:
        """Compute risk score for each cancer type, integrating CHAS modifier."""
        age_mod    = AGE_MODIFIERS.get(patient.age_group, 1.0)
        family_mod = FAMILY_HISTORY_MODIFIERS.get(patient.family_history, 1.0)
        smoke_mod  = 1.15 if patient.smoking else 1.0
        alc_mod    = 1.10 if patient.alcohol else 1.0
        bmi_mod    = 1.10 if patient.bmi_obese else 1.0
        hpylori_mod = 1.25 if patient.h_pylori else 1.0
        chas_mod   = chas.modifier()

        # Base demographic composite — CHAS replaces the old stacked modifiers
        demographic_base = age_mod * family_mod * smoke_mod * alc_mod * chas_mod

        results = []
        for cancer_type in CancerType:
            genomic_raw = 0.0
            symptom_raw = 0.0
            driving_vars = []
            amp_tiers_list = []

            # Genomic contribution
            for v in variants:
                vdata = self.variant_db[v]
                multiplier = vdata["risk_multipliers"].get(cancer_type, 0.0)
                if multiplier > 0:
                    genomic_raw += multiplier * 8.0
                    driving_vars.append(v)
                    amp_tiers_list.append(vdata["amp_tier"].value)

            # Symptom contribution
            for sym_id in symptoms:
                sym = SYMPTOM_WEIGHTS.get(sym_id)
                if sym and cancer_type in sym["cancers"]:
                    symptom_raw += sym["weight"] * 10.0

            # Cancer-specific modifiers
            cancer_mod = demographic_base
            if cancer_type == CancerType.GASTRIC:
                cancer_mod *= hpylori_mod
            if cancer_type in (CancerType.ESOPHAGEAL, CancerType.GASTRIC):
                cancer_mod *= bmi_mod

            raw        = (genomic_raw + symptom_raw) * cancer_mod
            normalised = self._normalise(raw)

            results.append(CancerRiskScore(
                cancer_type           = cancer_type.value,
                raw_score             = round(raw, 3),
                normalised_score      = round(normalised, 1),
                genomic_contribution  = round(genomic_raw, 3),
                symptom_contribution  = round(symptom_raw, 3),
                demographic_modifier  = round(cancer_mod, 3),
                chas_modifier         = round(chas_mod, 3),
                driving_variants      = driving_vars,
                amp_tiers             = list(set(amp_tiers_list)),
            ))

        return sorted(results, key=lambda x: x.normalised_score, reverse=True)

    def _normalise(self, raw: float) -> float:
        """Soft ceiling mapping raw score to 0-100."""
        if raw <= 0:
            return 0.0
        return min(100 * (1 - math.exp(-raw / 60)), 98.0)

    def _compute_composite(
        self,
        cancer_scores: list[CancerRiskScore],
        variants:      list[str],
    ) -> tuple[float, float]:
        """Weighted top-3 cancer composite + standalone genomic score."""
        top3    = cancer_scores[:3]
        weights = [0.50, 0.30, 0.20]
        composite = sum(cs.normalised_score * w for cs, w in zip(top3, weights))

        genomic_raw = 0.0
        for v in variants:
            vdata    = self.variant_db[v]
            max_mult = max(vdata["risk_multipliers"].values(), default=0.0)
            genomic_raw += max_mult * 8.0
        genomic_score = self._normalise(genomic_raw)

        return min(composite, 98.0), genomic_score

    def _classify_risk(
        self,
        composite:     float,
        cancer_scores: list[CancerRiskScore],
    ) -> tuple[RiskTier, str]:
        if composite >= 75:
            return RiskTier.CRITICAL, UrgencyAction.ONCOLOGY_2WK.value
        elif composite >= 55:
            return RiskTier.HIGH, UrgencyAction.IMAGING_PANEL.value
        elif composite >= 35:
            return RiskTier.MODERATE, UrgencyAction.FOLLOWUP_3MO.value
        elif composite >= 15:
            return RiskTier.ELEVATED, UrgencyAction.FOLLOWUP_3MO.value
        else:
            return RiskTier.ROUTINE, UrgencyAction.ANNUAL_SCREEN.value

    def _build_variant_results(self, variants: list[str]) -> list[VariantResult]:
        results = []
        for v in variants:
            vd = self.variant_db[v]
            results.append(VariantResult(
                variant          = v,
                gene_full        = vd["gene_full"],
                mechanism        = vd["mechanism"],
                inheritance      = vd["inheritance"],
                amp_tier         = vd["amp_tier"].value,
                amp_rationale    = vd["amp_rationale"],
                targeted_agents  = vd.get("targeted_agents", []),
                cancer_risks     = {ct.value: mult for ct, mult in vd["risk_multipliers"].items()},
                clinical_note    = vd["clinical_note"],
                reference        = vd["reference"],
            ))
        return results

    def _build_pharma_flags(
        self,
        pharma_variants:  dict[str, list[str]],
        genomic_variants: list[str],
    ) -> list[PharmacoFlag]:
        flagged = set(pharma_variants.keys())

        # Implicit flags from genomic context
        if any(v in genomic_variants for v in ["BRCA1", "BRCA2", "CDH1"]):
            flagged.add("CYP2D6")
        if any(v in genomic_variants for v in ["MLH1", "MSH2", "SMAD4"]):
            flagged.add("DPYD")
            flagged.add("UGT1A1")
        if "KRAS" in genomic_variants:
            flagged.add("CYP3A4")

        flags = []
        for enzyme in flagged:
            pd = self.pharma_db.get(enzyme)
            if not pd:
                continue
            flags.append(PharmacoFlag(
                enzyme             = enzyme,
                enzyme_full        = pd["enzyme_full"],
                affected_drugs     = pd["affected_drugs"],
                clinical_relevance = pd["clinical_relevance_oncology"],
                clinical_note      = pd["clinical_note"],
                cpic_guideline     = pd["cpic_guideline"],
            ))

        relevance_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2}
        flags.sort(key=lambda f: relevance_order.get(f.clinical_relevance, 9))
        return flags

    def _generate_recommendations(
        self,
        composite:     float,
        cancer_scores: list[CancerRiskScore],
        variants:      list[str],
        pharma_flags:  list[PharmacoFlag],
        patient:       PatientProfile,
        chas_result:   CHASResult,
    ) -> list[str]:
        recs = []

        pancreatic_score = next((cs.normalised_score for cs in cancer_scores if cs.cancer_type == "pancreatic"), 0)
        gastric_score    = next((cs.normalised_score for cs in cancer_scores if cs.cancer_type == "gastric"), 0)
        esophageal_score = next((cs.normalised_score for cs in cancer_scores if cs.cancer_type == "esophageal"), 0)

        if composite >= 55:
            recs.append("Contrast-enhanced CT abdomen and pelvis — urgent")

        if pancreatic_score > 25:
            recs.append("CA 19-9, CEA, amylase/lipase panel")
            recs.append("Pancreatic protocol MRI or endoscopic ultrasound (EUS)")

        if gastric_score > 25:
            recs.append("Upper GI endoscopy (OGD) with biopsies")
            recs.append("H. pylori testing (urea breath test or serology)")

        if esophageal_score > 25:
            recs.append("Barium swallow + upper GI endoscopy")
            recs.append("pH monitoring if reflux history present")

        # AMP Tier I–specific recommendations
        if "CDH1" in variants:
            recs.append(
                "[AMP Tier I] CDH1 — Refer to Hereditary Diffuse Gastric Cancer (HDGC) clinic; "
                "prophylactic total gastrectomy discussion indicated"
            )
        if any(v in variants for v in ["BRCA1", "BRCA2", "PALB2"]):
            recs.append(
                "[AMP Tier I/II] BRCA1/2/PALB2 — Annual pancreatic EUS/MRI from age 50 "
                "(or 10yr before earliest affected relative)"
            )
        if any(v in variants for v in ["MLH1", "MSH2"]):
            recs.append(
                "[AMP Tier I] Lynch syndrome — annual colonoscopy from age 25 + upper GI surveillance"
            )
        if "TP53" in variants:
            recs.append("[AMP Tier I] TP53 / Li-Fraumeni — whole-body MRI annually; avoid ionising radiation")

        if composite >= 35:
            recs.append("Genetic counselling referral for cascade testing of first-degree relatives")

        # CHAS-driven recommendations
        if chas_result.score >= 2:
            recs.append(
                f"CHAS score {chas_result.score} ({chas_result.interpretation}): "
                f"coordinate comorbidity management with internal medicine pre-treatment. "
                f"Active items: {', '.join(chas_result.active_items) or 'none'}"
            )
        if chas_result.score >= 4:
            recs.append(
                "High CHAS burden: review drug-drug interactions and renal/hepatic dosing "
                "adjustments for all planned chemotherapy agents"
            )

        # CPIC pharmacogenomic recommendations
        for flag in pharma_flags:
            if flag.clinical_relevance == "CRITICAL":
                recs.append(
                    f"PHARMACOGENOMICS CRITICAL — {flag.enzyme}: "
                    f"review {', '.join(flag.affected_drugs[:2])} dosing before treatment initiation. "
                    f"Guideline: {flag.cpic_guideline}"
                )

        # Surveillance
        if composite >= 15:
            recs.append("3-monthly symptom surveillance with primary care")
        else:
            recs.append("Annual surveillance with primary care review")

        return recs


# ─────────────────────────────────────────────
# UTILITY: PRETTY PRINT REPORT
# ─────────────────────────────────────────────

def print_report(report: RiskReport) -> None:
    sep = "─" * 72
    print(f"\n{sep}")
    print(f"  OncosenseAI — Module 5 Genomic Risk Report")
    print(f"  Generated: {report.timestamp}")
    print(f"{sep}")

    print(f"\n  PATIENT PROFILE")
    p = report.patient_profile
    print(f"  Age group      : {p.age_group}")
    print(f"  Sex            : {p.sex}")
    print(f"  Family history : {p.family_history}")
    print(f"  Smoking        : {'Yes' if p.smoking else 'No'}")
    print(f"  Alcohol        : {'Yes' if p.alcohol else 'No'}")
    print(f"  H. pylori      : {'Yes' if p.h_pylori else 'No'}")

    print(f"\n  CHAS COMORBIDITY SCORE")
    cr = report.chas_result
    print(f"  Score          : {cr.score}")
    print(f"  Modifier       : {cr.modifier:.2f}×")
    print(f"  Interpretation : {cr.interpretation}")
    if cr.active_items:
        print(f"  Active items   : {', '.join(cr.active_items)}")

    print(f"\n  VARIANTS ASSESSED (AMP/ASCO/CAP Tiers)")
    for vr in report.variant_results:
        print(f"  {vr.variant:<8} Tier {vr.amp_tier}  {vr.gene_full}")
        print(f"           {vr.amp_rationale[:80]}...")

    print(f"\n  COMPOSITE RISK SCORE : {report.composite_score:.1f} / 100")
    print(f"  GENOMIC SCORE        : {report.genomic_score:.1f} / 100")
    print(f"  RISK TIER            : {report.risk_tier.value}")
    print(f"  URGENCY              : {report.urgency_action}")

    print(f"\n  CANCER-SPECIFIC RISK SCORES (top 5)")
    for cs in report.cancer_scores[:5]:
        bar = "█" * int(cs.normalised_score / 5) + "░" * (20 - int(cs.normalised_score / 5))
        amp_str = f"  AMP: {', '.join(cs.amp_tiers)}" if cs.amp_tiers else ""
        print(f"  {cs.cancer_type:<14} {bar} {cs.normalised_score:5.1f}%  CHAS mod: {cs.chas_modifier:.2f}×{amp_str}")

    if report.pharma_flags:
        print(f"\n  PHARMACOGENOMIC FLAGS (CPIC)")
        for pf in report.pharma_flags:
            print(f"\n  {pf.enzyme} ({pf.enzyme_full})")
            print(f"  Relevance  : {pf.clinical_relevance}")
            print(f"  Drugs      : {', '.join(pf.affected_drugs[:4])}")
            print(f"  Note       : {pf.clinical_note[:120]}...")
            print(f"  Guideline  : {pf.cpic_guideline}")

    print(f"\n  CLINICAL RECOMMENDATIONS")
    for i, rec in enumerate(report.clinical_recommendations, 1):
        print(f"  {i:2}. {rec}")

    print(f"\n{sep}")
    print(f"  ⚕ {report.disclaimer[:100]}...")
    print(f"{sep}\n")


# ─────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    engine = GenomicRiskEngine()

    # Example 1: High-risk patient — BRCA2 + CDH1 + CHAS score 3
    patient_a = PatientProfile(
        age_group      = "51-60",
        sex            = "Female",
        family_history = "Multiple relatives",
        smoking        = False,
        alcohol        = False,
        h_pylori       = True,
    )
    chas_a = CHASProfile(
        hypertension    = True,
        diabetes_mellitus = True,
        h_pylori        = True,  # Synced with patient profile
    )
    report_a = engine.assess(
        patient         = patient_a,
        variants        = ["BRCA2", "CDH1", "ATM"],
        symptoms        = ["weight_loss", "early_satiety", "abdominal_pain"],
        pharma_variants = {"DPYD": ["DPYD*2A"]},
        chas            = chas_a,
    )
    print_report(report_a)

    # Example 2: Lynch syndrome carrier — CHAS score 4
    patient_b = PatientProfile(
        age_group      = "41-50",
        sex            = "Male",
        family_history = "First-degree",
        smoking        = True,
        alcohol        = True,
    )
    chas_b = CHASProfile(
        coronary_heart_disease = True,
        hypertension           = True,
        diabetes_mellitus      = True,
        ckd_renal_impairment   = True,
    )
    report_b = engine.assess(
        patient  = patient_b,
        variants = ["MLH1", "CDKN2A"],
        symptoms = ["heartburn", "weight_loss"],
        chas     = chas_b,
    )
    print_report(report_b)

    # JSON output for API
    print("JSON output (first 600 chars):")
    print(engine.report_to_json(report_a)[:600] + "...\n")

    # Parse report text
    sample_text = """
    23andMe Genetic Health Risk Report
    Variants detected: BRCA2 pathogenic, ATM heterozygous
    Pharmacogenomics: DPYD*2A detected, CYP2D6*4 detected
    """
    parsed = engine.parse_report_text(sample_text)
    print("Parsed report text:")
    print(f"  Genomic variants : {parsed['detected_variants']}")
    print(f"  AMP tiers        : {parsed['amp_tiers']}")
    print(f"  Pharma variants  : {parsed['detected_pharma']}")
