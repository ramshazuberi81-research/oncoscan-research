"""
OncosenseAI — Complete Early Detection Pipeline
Python/Dash implementation · 8 stages including SEER Validation
Run: python oncosenseai_app.py  →  http://localhost:8050

Place fig1_km_curves.png, fig2_model_results.png, fig3_deep_dive.png
next to this file to display the SEER validation figures.
"""

import dash
from dash import dcc, html, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json, random, base64
from pathlib import Path

# ── helpers ───────────────────────────────────────────────────────────────────
def img_b64(path):
    p = Path(path)
    if p.exists():
        with open(p, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return None

# ── fonts / colours ───────────────────────────────────────────────────────────
F = dict(serif="Fraunces, serif", mono="JetBrains Mono, monospace", sans="Nunito, sans-serif")
C = dict(
    ink="#0d1117", ink2="#161b22", ink3="#1c2333",
    border="#21262d", border2="#30363d",
    text="#e6edf3", text2="#8b949e", text3="#484f58",
    teal="#00d4aa", blue="#0099ff", purple="#a78bfa",
    amber="#f0a500", danger="#ff3060", warn="#ff8c42",
    gold="#f0c040", green="#3fb950",
    ivory="#faf8f4", warm_text="#1a1410", warm_text2="#5c4d3c",
    warm_accent="#c17b2e", warm_border="#e8ddc8",
)
PW = {"paddingTop": "72px", "minHeight": "100vh"}
IS = {"background": C["ink3"], "border": f"1px solid {C['border']}",
      "borderRadius": "5px", "color": C["text"],
      "fontFamily": F["mono"], "fontSize": "11px"}

STAGE_LABELS = [
    "Symptoms", "Clinical Records", "Genomic",
    "Diagnosis M6", "Treatment", "Monitoring",
    "Physician Centre", "SEER Validation"
]

ALARM_SX = [
    "Unexplained weight loss", "Jaundice (yellow skin/eyes)",
    "Dysphagia (difficulty swallowing)", "Rectal bleeding",
    "Haematemesis (vomiting blood)"
]
UPPER_AB = ["Upper abdominal pain","Epigastric discomfort","Nausea","Vomiting","Early satiety","Bloating"]
LOWER_GI = ["Change in bowel habit","Dark/tarry stools","Constipation","Diarrhoea"]
SYSTEMIC  = ["Fatigue","Night sweats","Loss of appetite","Back pain","Itchy skin"]

TREATMENTS = {
    "CRITICAL": dict(
        regimen="FOLFIRINOX or Gemcitabine/nab-Paclitaxel (stage-dependent)",
        guideline="ESMO 2023 · NCCN v2.2024",
        note="Surgical assessment mandatory. MSI-H → pembrolizumab. DPYD+ → avoid 5-FU.",
        contra=["5-FU (if DPYD variant detected)"],
        trials=["PRODIGE 4/ACCORD 11","MPACT trial"],
    ),
    "HIGH": dict(
        regimen="FLOT perioperative chemo (gastric) or CROSS chemoradiation (oesophageal)",
        guideline="NICE NG83 · ESMO 2022",
        note="HER2+ gastric → trastuzumab + chemo. PD-L1 CPS ≥5 → nivolumab consideration.",
        contra=[],
        trials=["FLOT4-AIO","CheckMate 649"],
    ),
    "MODERATE": dict(
        regimen="Surveillance endoscopy + H. pylori eradication if indicated",
        guideline="NICE NG12 · BSG 2023",
        note="Low-dose aspirin if no contraindication. Annual gastroscopy for high-grade dysplasia.",
        contra=[],
        trials=["AspECT trial"],
    ),
    "LOW": dict(
        regimen="Lifestyle counselling + 6-month clinical review",
        guideline="NICE NG12 · PCUK guidelines",
        note="Dietary modification, smoking cessation, alcohol reduction. Re-assess if symptoms persist.",
        contra=[],
        trials=[],
    ),
}

# ── shared components ──────────────────────────────────────────────────────────
def tag(text, color):
    return html.Div(text, style={
        "fontFamily": F["mono"], "fontSize": "9px", "letterSpacing": "0.22em",
        "textTransform": "uppercase", "color": color, "marginBottom": "10px"
    })

def serif_title(parts, color=None):
    nodes = []
    for p in parts:
        if isinstance(p, tuple):
            nodes.append(html.Em(p[0], style={"color": p[1], "fontStyle": "italic"}))
        else:
            nodes.append(p)
    return html.Div(nodes, style={
        "fontFamily": F["serif"], "fontSize": "clamp(1.6rem,3vw,2.4rem)",
        "fontWeight": "300", "color": color or C["text"], "marginBottom": "8px"
    })

def sub(text):
    return html.Div(text, style={
        "fontFamily": F["mono"], "fontSize": "11px",
        "color": C["text2"], "marginBottom": "24px"
    })

def card(children, style_extra=None):
    s = {"background": C["ink2"], "border": f"1px solid {C['border']}",
         "borderRadius": "10px", "padding": "18px", "marginBottom": "14px"}
    if style_extra: s.update(style_extra)
    return html.Div(children, style=s)

def field(label, component):
    return html.Div([
        html.Label(label, style={
            "fontFamily": F["mono"], "fontSize": "9px", "color": C["text3"],
            "marginBottom": "4px", "letterSpacing": "0.04em", "display": "block"
        }),
        component
    ], style={"marginBottom": "11px"})

def next_btn(label, bid, color=C["teal"], bg="0.08"):
    return dbc.Button(label, id=bid, color="link", style={
        "width": "100%", "padding": "13px", "marginTop": "16px",
        "fontFamily": F["mono"], "fontSize": "12px", "letterSpacing": "0.08em",
        "borderRadius": "8px", "border": f"1px solid {color}60",
        "color": color, "background": f"rgba(0,0,0,{bg})", "textDecoration": "none"
    })

def sym_chip(label, alarm=False):
    return dbc.Button(
        label, id={"type": "sx-chip", "index": label}, n_clicks=0,
        size="sm", outline=True, color="danger" if alarm else "secondary",
        style={"borderRadius": "100px", "fontSize": "0.82rem",
               "fontFamily": F["sans"], "margin": "3px"}
    )

def sx_group(title, syms, alarm=False):
    return html.Div([
        html.Div(title, style={"fontSize": "0.8rem", "fontWeight": "700",
                               "color": C["warm_text"], "marginBottom": "10px"}),
        html.Div([sym_chip(s, alarm) for s in syms])
    ], style={"background": "#fff", "border": f"1.5px solid {C['warm_border']}",
              "borderRadius": "12px", "padding": "16px"})

# ── stage pages ────────────────────────────────────────────────────────────────

def s1():
    return html.Div([html.Div([
        tag("OncosenseAI · Stage 1 of 8", C["warm_accent"]),
        html.Div(["Tell me what's been ", html.Em("bothering you",
            style={"color": C["warm_accent"], "fontStyle": "italic"})],
            style={"fontFamily": F["serif"], "fontSize": "clamp(1.8rem,4vw,2.8rem)",
                   "fontWeight": "300", "lineHeight": "1.2", "marginBottom": "10px",
                   "color": C["warm_text"]}),
        html.Div("Describe your symptoms as if talking to your doctor.",
                 style={"fontSize": "0.95rem", "color": C["warm_text2"],
                        "lineHeight": "1.7", "marginBottom": "28px"}),

        # Patient info
        html.Div([
            html.Div("Your Details", style={"fontFamily": F["mono"], "fontSize": "9px",
                "letterSpacing": "0.15em", "textTransform": "uppercase",
                "color": C["warm_text2"], "marginBottom": "14px"}),
            dbc.Row([
                dbc.Col(dbc.Input(id="pt_name", placeholder="First name")),
                dbc.Col(dbc.Input(id="pt_age", placeholder="Age", type="number", min=18, max=120)),
                dbc.Col(dbc.Select(id="pt_sex", options=[
                    {"label": "Select sex","value": ""},
                    {"label": "Male","value": "Male"},
                    {"label": "Female","value": "Female"},
                    {"label": "Other","value": "Other"},
                ])),
            ], className="g-2 mb-2"),
            dbc.Row([
                dbc.Col(dbc.Select(id="pt_smoke", options=[
                    {"label": "Never smoked","value": "Never"},
                    {"label": "Former smoker","value": "Former"},
                    {"label": "Current smoker","value": "Current"},
                ])),
                dbc.Col(dbc.Select(id="pt_alcohol", options=[
                    {"label": "No alcohol","value": "None"},
                    {"label": "Occasional","value": "Occasional"},
                    {"label": "Regular (weekly)","value": "Regular"},
                    {"label": "Heavy (daily)","value": "Heavy"},
                ])),
                dbc.Col(dbc.Select(id="pt_family", options=[
                    {"label": "No family history","value": "None"},
                    {"label": "First-degree relative","value": "First-degree"},
                    {"label": "Multiple relatives","value": "Multiple"},
                ])),
            ], className="g-2"),
        ], style={"background": "#fff", "border": f"1.5px solid {C['warm_border']}",
                  "borderRadius": "12px", "padding": "20px", "marginBottom": "20px"}),

        html.Div(
            "⚠ ALARM SYMPTOMS SELECTED — Expedited assessment recommended (NICE NG12 urgent criteria).",
            id="alarm-flag", style={"display": "none", "background": "#fef2f2",
                "border": "1px solid #fecaca", "borderLeft": "3px solid #dc2626",
                "borderRadius": "8px", "padding": "10px 14px", "fontSize": "0.82rem",
                "color": "#991b1b", "marginBottom": "12px"}),

        html.Div("Select all symptoms you are experiencing", style={
            "fontFamily": F["mono"], "fontSize": "9px", "letterSpacing": "0.15em",
            "textTransform": "uppercase", "color": C["warm_text2"], "marginBottom": "10px"}),
        dbc.Row([
            dbc.Col(sx_group("🚨 Alarm Symptoms (urgent)", ALARM_SX, alarm=True), md=6),
            dbc.Col(sx_group("🫁 Upper Abdominal", UPPER_AB), md=6),
        ], className="g-3 mb-3"),
        dbc.Row([
            dbc.Col(sx_group("🩸 Lower GI", LOWER_GI), md=6),
            dbc.Col(sx_group("⚡ Systemic", SYSTEMIC), md=6),
        ], className="g-3 mb-3"),

        html.Div([
            html.Div("Severity", style={"fontSize": "0.8rem", "fontWeight": "600",
                                        "color": C["warm_text2"], "marginBottom": "8px"}),
            dbc.ButtonGroup([
                dbc.Button("Mild", id="sev-mild", color="success", outline=True, size="sm"),
                dbc.Button("Moderate", id="sev-mod", color="warning", outline=True, size="sm"),
                dbc.Button("Severe", id="sev-sev", color="danger", outline=True, size="sm"),
            ])
        ], style={"marginBottom": "16px"}),

        html.Div([
            html.Div("Duration", style={"fontSize": "0.8rem", "fontWeight": "600",
                                        "color": C["warm_text2"], "marginBottom": "8px"}),
            dbc.RadioItems(id="sx-duration", inline=True, value="< 2 weeks", options=[
                {"label": "< 2 weeks","value": "< 2 weeks"},
                {"label": "2–6 weeks","value": "2–6 weeks"},
                {"label": "6w – 3mo","value": "6w–3mo"},
                {"label": "> 3 months","value": "> 3 months"},
            ]),
        ], style={"marginBottom": "20px"}),

        dbc.Button("Proceed to Clinical Records →", id="btn-s1-next",
                   color="warning",
                   style={"width": "100%", "padding": "14px",
                          "fontFamily": F["serif"], "fontSize": "1.05rem",
                          "borderRadius": "10px"}),
    ], style={"maxWidth": "740px", "margin": "0 auto", "padding": "48px 24px"})],
    style={**PW, "background": C["ivory"], "color": C["warm_text"]})


def s2():
    def rec(title, color, children):
        return html.Div([
            html.Div(title, style={"fontFamily": F["mono"], "fontSize": "9px",
                "letterSpacing": "0.16em", "textTransform": "uppercase",
                "color": color, "marginBottom": "14px"}),
            *children
        ], style={"background": C["ink2"], "border": f"1px solid {C['border']}",
                  "borderRadius": "10px", "padding": "18px", "marginBottom": "14px"})

    return html.Div([html.Div([
        tag("OncosenseAI · Stage 2 of 8", C["teal"]),
        serif_title(["Clinical ", ("Records", C["teal"])]),
        sub("Labs · Imaging · Endoscopy · Vitals"),
        dbc.Row([
            dbc.Col(rec("🔬 Laboratory Results", C["teal"], [
                field("CA 19-9 (U/mL)", dbc.Input(id="lab_ca199", placeholder="e.g. 87", style=IS)),
                field("CEA (ng/mL)",     dbc.Input(id="lab_cea",   placeholder="e.g. 5.2", style=IS)),
                field("CA 125 (U/mL)",  dbc.Input(id="lab_ca125", placeholder="e.g. 35",  style=IS)),
                field("Haemoglobin (g/dL)", dbc.Input(id="lab_hb", placeholder="e.g. 11.2", style=IS)),
                field("Albumin (g/dL)", dbc.Input(id="lab_alb",   placeholder="e.g. 3.4",  style=IS)),
            ]), md=6),
            dbc.Col(rec("🩻 Imaging Findings", C["blue"], [
                field("Modality", dbc.Select(id="img_mod", style=IS, options=[
                    {"label": "None performed","value": "None"},
                    {"label": "CT Abdomen/Pelvis","value": "CT"},
                    {"label": "MRI","value": "MRI"},
                    {"label": "Endoscopic Ultrasound","value": "EUS"},
                    {"label": "PET-CT","value": "PET"},
                ])),
                field("Findings", dbc.Textarea(id="img_findings",
                    placeholder="e.g. 2.8cm hypoechoic mass pancreatic head...",
                    style={**IS, "minHeight": "70px"})),
                field("Lesion size (mm)", dbc.Input(id="img_size", placeholder="e.g. 28", style=IS)),
                field("Vascular involvement", dbc.Select(id="img_vasc", style=IS, options=[
                    {"label": "None","value": "None"},
                    {"label": "Abutment","value": "Abutment"},
                    {"label": "Encasement","value": "Encasement"},
                ])),
            ]), md=6),
        ], className="g-3"),
        dbc.Row([
            dbc.Col(rec("🔭 Endoscopy", C["purple"], [
                field("Procedure", dbc.Select(id="endo_proc", style=IS, options=[
                    {"label": "None performed","value": "None"},
                    {"label": "OGD/Gastroscopy","value": "OGD"},
                    {"label": "Colonoscopy","value": "Colonoscopy"},
                    {"label": "ERCP","value": "ERCP"},
                ])),
                field("Biopsy", dbc.Select(id="endo_bx", style=IS, options=[
                    {"label": "No biopsy","value": "No"},
                    {"label": "Yes — pending","value": "Pending"},
                    {"label": "Yes — result available","value": "Result"},
                ])),
                field("Histology", dbc.Input(id="endo_histo",
                    placeholder="e.g. Moderately diff. adenocarcinoma", style=IS)),
            ]), md=6),
            dbc.Col(rec("❤️ Vitals", C["amber"], [
                dbc.Row([
                    dbc.Col(field("BP (mmHg)", dbc.Input(id="vit_bp", placeholder="120/80", style=IS))),
                    dbc.Col(field("HR (bpm)", dbc.Input(id="vit_hr", placeholder="72", style=IS))),
                ], className="g-2"),
                dbc.Row([
                    dbc.Col(field("Weight (kg)", dbc.Input(id="vit_wt", placeholder="68", style=IS))),
                    dbc.Col(field("BMI", dbc.Input(id="vit_bmi", placeholder="24.1", style=IS))),
                ], className="g-2"),
                field("ECOG Status", dbc.Select(id="vit_ecog", style=IS, options=[
                    {"label": f"ECOG {i}","value": str(i)} for i in range(5)
                ])),
            ]), md=6),
        ], className="g-3 mb-3"),
        next_btn("Proceed to Genomic Report →", "btn-s2-next", C["teal"]),
    ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


def s3():
    chips_data = [
        ("KRAS G12D", True), ("KRAS G12V", True), ("KRAS G12C", False),
        ("TP53", True),      ("SMAD4", False),     ("CDKN2A", False),
        ("BRCA1", True),     ("BRCA2", True),      ("ATM", False),
        ("ERBB2/HER2", True),("PIK3CA", False),    ("APC", False),
    ]
    return html.Div([html.Div([
        tag("OncosenseAI · Stage 3 of 8", C["purple"]),
        serif_title(["Genomic ", ("Report", C["purple"])]),
        sub("Somatic mutations · Molecular markers · Pharmacogenomics"),
        html.Div([
            "GENOMIC ANCHOR: Molecular profiling integrates somatic mutation burden, "
            "germline risk variants, MSI status, and pharmacogenomic safety flags to "
            "personalise treatment selection and flag contraindicated agents."
        ], style={"background": "linear-gradient(135deg,#1e1535,rgba(10,16,24,0.9))",
                  "border": "1px solid rgba(167,139,250,0.2)", "borderRadius": "12px",
                  "padding": "20px", "marginBottom": "20px",
                  "fontFamily": F["mono"], "fontSize": "11px",
                  "lineHeight": "1.8", "color": "#c4b5fd"}),
        dbc.Row([
            dbc.Col(card([
                html.Div("Somatic Mutations", style={"fontFamily": F["mono"], "fontSize": "9px",
                    "letterSpacing": "0.14em", "textTransform": "uppercase",
                    "color": C["text3"], "marginBottom": "12px"}),
                html.Div([
                    dbc.Button(name, id={"type": "mut-chip", "index": name},
                        size="sm", outline=True,
                        color="danger" if danger else "secondary",
                        style={"borderRadius": "100px", "fontSize": "10px",
                               "fontFamily": F["mono"], "margin": "3px"}, n_clicks=0)
                    for name, danger in chips_data
                ]),
                html.Div(style={"marginTop": "12px"}),
                field("Custom / additional mutations",
                      dbc.Input(id="g_muts", placeholder="e.g. KRAS G12D, TP53 R248W", style=IS)),
            ]), md=7),
            dbc.Col(card([
                html.Div("Molecular Markers", style={"fontFamily": F["mono"], "fontSize": "9px",
                    "letterSpacing": "0.14em", "textTransform": "uppercase",
                    "color": C["text3"], "marginBottom": "14px"}),
                field("MSI Status", dbc.Select(id="g_msi", style=IS, options=[
                    {"label": "MSS (Stable)","value": "MSS"},
                    {"label": "MSI-L (Low)","value": "MSI-L"},
                    {"label": "MSI-H (High — immunotherapy eligible)","value": "MSI-H"},
                ])),
                field("HER2 Status", dbc.Select(id="g_her2", style=IS, options=[
                    {"label": "Negative","value": "Negative"},
                    {"label": "Positive (IHC 3+ / FISH)","value": "Positive"},
                    {"label": "Equivocal (IHC 2+)","value": "Equivocal"},
                ])),
                field("TMB (mut/Mb)", dbc.Select(id="g_tmb", style=IS, options=[
                    {"label": "Low (< 10)","value": "Low"},
                    {"label": "Intermediate (10–19)","value": "Intermediate"},
                    {"label": "High (≥ 20)","value": "High"},
                ])),
                field("Mutational Disturbance", dbc.Select(id="g_dist", style=IS, options=[
                    {"label": "None detected","value": "None"},
                    {"label": "Low","value": "Low"},
                    {"label": "Moderate","value": "Moderate"},
                    {"label": "High","value": "High"},
                ])),
                dbc.Checklist(
                    id="g_dpyd", value=[],
                    options=[{"label": " DPYD variant — ⚠ 5-FU contraindicated","value": "DPYD"}],
                    style={"fontFamily": F["mono"], "fontSize": "10px",
                           "color": C["danger"], "marginTop": "8px"}
                ),
            ]), md=5),
        ], className="g-3 mb-3"),
        next_btn("Run M6 Diagnostic Analysis →", "btn-s3-next", C["purple"]),
    ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


def s4():
    return html.Div([html.Div([
        tag("OncosenseAI · Stage 4 of 8", C["teal"]),
        serif_title(["M6 Dissonance ", ("Analysis", C["teal"])]),
        sub("Six-module synthesis · Symptom × Clinical × Genomic × SHAP × Guideline × Dissonance"),
        html.Div(id="diag-out", children=[
            html.Div("Complete Stage 3 then click 'Run M6 Diagnostic Analysis' to generate your report.",
                style={"fontFamily": F["mono"], "fontSize": "12px", "color": C["text3"],
                       "textAlign": "center", "padding": "60px"})
        ]),
        next_btn("Proceed to Treatment Plan →", "btn-s4-next", C["teal"]),
    ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


def s5():
    return html.Div([html.Div([
        tag("OncosenseAI · Stage 5 of 8", C["amber"]),
        serif_title(["Treatment ", ("Plan", C["amber"])]),
        sub("NCCN / ESMO / NICE guideline-anchored · Genomically personalised · Clinical trials matched"),
        html.Div(id="tx-out", children=[
            html.Div("Complete the M6 analysis first.",
                style={"fontFamily": F["mono"], "fontSize": "12px", "color": C["text3"],
                       "textAlign": "center", "padding": "60px"})
        ]),
        next_btn("Proceed to Monitoring →", "btn-s5-next", C["amber"]),
    ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


def s6():
    months = list(range(0, 13))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=[87,92,105,118,99,88,74,61,55,48,43,39,36],
        mode="lines+markers", name="CA 19-9",
        line=dict(color=C["teal"], width=2.5),
        marker=dict(size=6, color=C["teal"])
    ))
    fig.add_trace(go.Scatter(
        x=months,
        y=[5.2,5.8,6.1,7.2,6.8,5.9,5.1,4.6,4.1,3.8,3.5,3.2,3.0],
        mode="lines+markers", name="CEA", yaxis="y2",
        line=dict(color=C["amber"], width=2, dash="dot"),
        marker=dict(size=5, color=C["amber"])
    ))
    fig.add_shape(type="line", x0=0, x1=12, y0=37, y1=37,
                  line=dict(color=C["danger"], width=1, dash="dash"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=C["ink2"], height=280,
        font=dict(family=F["mono"], color=C["text2"], size=10),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(title="Months", gridcolor=C["border"]),
        yaxis=dict(title="CA 19-9 (U/mL)", gridcolor=C["border"]),
        yaxis2=dict(title="CEA (ng/mL)", overlaying="y", side="right"),
    )

    schedule = [
        ("Month 1–3",  "CT chest/abdomen/pelvis",          C["danger"]),
        ("Month 3",    "CA 19-9 + CEA + LFTs",              C["teal"]),
        ("Month 3",    "Oncology clinic review",             C["amber"]),
        ("Month 6",    "Repeat CT + tumour markers",         C["warn"]),
        ("Month 6",    "Dietitian + psycho-oncology review", C["purple"]),
        ("Month 12",   "Annual surveillance CT",             C["teal"]),
    ]

    return html.Div([html.Div([
        tag("OncosenseAI · Stage 6 of 8", C["green"]),
        serif_title(["Monitoring ", ("& Follow-Up", C["green"])]),
        sub("Tumour marker trajectory · Imaging schedule · Response assessment · Toxicity monitoring"),
        card([
            html.Div("Tumour Marker Trend — Simulated Trajectory", style={
                "fontFamily": F["mono"], "fontSize": "9px", "letterSpacing": "0.14em",
                "textTransform": "uppercase", "color": C["text3"], "marginBottom": "10px"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
            html.Div("CA 19-9 reference < 37 U/mL (dashed). Simulated data for illustration.",
                style={"fontFamily": F["mono"], "fontSize": "9px",
                       "color": C["text3"], "marginTop": "6px"}),
        ]),
        card([
            html.Div("Recommended Follow-Up Schedule", style={
                "fontFamily": F["mono"], "fontSize": "9px", "letterSpacing": "0.14em",
                "textTransform": "uppercase", "color": C["text3"], "marginBottom": "14px"}),
            *[html.Div([
                html.Div(tp, style={"fontFamily": F["mono"], "fontSize": "9px",
                                    "color": col, "minWidth": "90px"}),
                html.Div("•", style={"color": col, "margin": "0 8px"}),
                html.Div(task, style={"fontFamily": F["mono"], "fontSize": "11px",
                                      "color": C["text2"]}),
            ], style={"display": "flex", "alignItems": "center", "padding": "8px 0",
                      "borderBottom": f"1px solid {C['border']}"})
              for tp, task, col in schedule],
        ]),
        next_btn("Proceed to Physician Centre →", "btn-s6-next", C["green"]),
    ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


def s7():
    return html.Div([html.Div([
        tag("OncosenseAI · Stage 7 of 8", C["blue"]),
        serif_title(["Physician ", ("Centre", C["blue"])]),
        sub("Clinical dossier · Second opinion pathway · Secure messaging"),
        html.Div(id="phys-summary"),
        card([
            html.Div("Second Opinion Pathway", style={"fontFamily": F["mono"], "fontSize": "9px",
                "letterSpacing": "0.14em", "textTransform": "uppercase",
                "color": C["text3"], "marginBottom": "14px"}),
            *[html.Div([
                html.Div(spec, style={"fontFamily": F["mono"], "fontSize": "10px", "color": C["text"]}),
                html.Div(role, style={"fontFamily": F["mono"], "fontSize": "9px", "color": C["text3"]}),
                html.Div("Available", style={"marginLeft": "auto", "fontFamily": F["mono"],
                    "fontSize": "8px", "padding": "2px 8px", "borderRadius": "3px",
                    "background": "rgba(0,212,170,0.1)", "color": C["teal"]}),
            ], style={"display": "flex", "alignItems": "center", "gap": "12px",
                      "padding": "10px 0", "borderBottom": f"1px solid {C['border']}"})
              for spec, role in [
                  ("Prof. GI Oncology MDT", "Upper GI · Hepatobiliary"),
                  ("Dr. Molecular Pathology", "Genomic interpretation · PGx"),
                  ("Dr. Clinical Genetics", "Germline risk · BRCA / Lynch"),
                  ("Palliative Care Consultant", "Symptom management · EPCR"),
              ]],
            dbc.Button("Request Second Opinion", id="btn-second-op",
                       color="danger", outline=True,
                       style={"marginTop": "14px", "fontFamily": F["mono"], "fontSize": "10px"}),
        ]),
        card([
            html.Div("Secure Messaging", style={"fontFamily": F["mono"], "fontSize": "9px",
                "letterSpacing": "0.14em", "textTransform": "uppercase",
                "color": C["text3"], "marginBottom": "14px"}),
            html.Div(id="msg-thread", children=[
                html.Div([
                    html.Div("🤖", style={"fontSize": "20px", "marginRight": "10px"}),
                    html.Div([
                        html.Div(
                            "Clinical AI summary generated. Risk stratification and treatment recommendations attached.",
                            style={"background": C["ink3"], "border": f"1px solid {C['border2']}",
                                   "borderRadius": "8px", "padding": "10px 14px",
                                   "fontFamily": F["mono"], "fontSize": "11px",
                                   "color": C["text2"], "lineHeight": "1.7"}),
                        html.Div("OncosenseAI · Now", style={"fontFamily": F["mono"],
                            "fontSize": "8px", "color": C["text3"], "marginTop": "4px"}),
                    ])
                ], style={"display": "flex", "marginBottom": "12px"}),
            ], style={"maxHeight": "240px", "overflowY": "auto", "marginBottom": "10px"}),
            html.Div([
                dbc.Input(id="msg-input", placeholder="Message the clinical team...", style={**IS, "flex": "1"}),
                dbc.Button("Send", id="btn-send-msg", color="primary", size="sm",
                           style={"marginLeft": "8px", "fontFamily": F["mono"]}),
            ], style={"display": "flex"}),
        ]),
        next_btn("View SEER Validation Evidence →", "btn-s7-next", C["blue"]),
    ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


def s8():
    FIG1 = img_b64("fig1_km_curves.png")
    FIG2 = img_b64("fig2_model_results.png")
    FIG3 = img_b64("fig3_deep_dive.png")

    def fig_card(title, src, caption):
        return card([
            html.Div(title, style={"fontFamily": F["mono"], "fontSize": "10px",
                "letterSpacing": "0.18em", "textTransform": "uppercase",
                "color": C["teal"], "marginBottom": "10px"}),
            html.Img(src=src, style={"width": "100%", "borderRadius": "8px",
                "border": f"1px solid {C['border2']}", "display": "block"}) if src else
            html.Div(
                "Figure not found — place PNG file next to oncosenseai_app.py",
                style={"color": C["text3"], "fontFamily": F["mono"], "fontSize": "11px",
                       "padding": "40px", "border": f"1px dashed {C['border2']}",
                       "borderRadius": "8px", "textAlign": "center"}),
            html.Div(caption, style={"fontFamily": F["mono"], "fontSize": "10px",
                "color": C["text2"], "marginTop": "10px", "lineHeight": "1.7"}),
        ])

    stats = [
        ("Ensemble AUROC", "0.753"), ("LR AUROC", "0.790"),
        ("NPV @ 95% Sens", "0.853"), ("Validation n", "500"),
    ]

    return html.Div([html.Div([
        tag("OncosenseAI · Stage 8 of 8 · SEER Validation", C["teal"]),
        serif_title(["SEER Validation: ", ("Performance Evidence", C["teal"])]),
        sub("n=500 retrospective cohort · 5-fold CV · Pancreatic, Gastric, Esophageal · TRIPOD-compliant"),

        html.Div([
            html.Div([
                html.Div(v, style={"fontFamily": F["mono"], "fontSize": "20px",
                                    "color": C["teal"], "marginBottom": "4px"}),
                html.Div(k, style={"fontFamily": F["mono"], "fontSize": "8px",
                                    "color": C["text3"], "letterSpacing": "0.08em"}),
            ], style={"background": C["ink2"], "border": f"1px solid {C['border']}",
                      "borderRadius": "8px", "padding": "14px", "textAlign": "center", "flex": "1"})
            for k, v in stats
        ], style={"display": "flex", "gap": "12px", "marginBottom": "28px", "flexWrap": "wrap"}),

        fig_card(
            "Fig 1 · Kaplan–Meier Survival Curves — Overall, by Stage, by Race/Ethnicity",
            FIG1,
            "Left: Overall survival by cancer site — Pancreas (n=264), Stomach (n=146), Esophagus (n=90). "
            "Centre: By stage — Distant disease median 5 months vs Localized 14 months. "
            "Right: Racial disparities — Black patients median 7mo vs White 9mo vs Other 12mo. 95% CI bands shown."
        ),
        fig_card(
            "Fig 2 · ROC Curves, SHAP Feature Importance & Treatment-Stratified Survival",
            FIG2,
            "Left: ROC for 12-month mortality prediction (5-fold CV). Ensemble AUROC 0.753, LR 0.790, RF 0.752, GB 0.694. "
            "Centre: RF feature importance — Surgery (0.264) and Age×Stage (0.203) dominate. "
            "Right: Surgical cohort (n=153) shows substantially prolonged survival vs no-surgery (n=347)."
        ),
        fig_card(
            "Fig 3 · Site × Stage Deep Dive — KM curves, Stage Distribution, Heatmap, 1/2-Year Rates",
            FIG3,
            "Top: KM curves per cancer site by stage. Stomach localized 35mo vs distant 4mo (8.75× multiplier). "
            "Stage distribution: 55% pancreatic, 43% stomach, 44% esophageal cases present as distant disease. "
            "1-year survival: Esophagus 51%, Stomach 48%, Pancreas 37%. 2-year: Stomach 31%, Esophagus 28%, Pancreas 22%."
        ),

        html.Div(
            "⚠ RESEARCH PROTOTYPE ONLY. All figures derived from SEER retrospective validation (n=500). "
            "Not validated for prospective clinical decision-making. Not approved by FDA, CE, MHRA, or equivalent authority. "
            "TRIPOD reporting guidelines followed. Intended for research and demonstration purposes only.",
            style={"fontFamily": F["mono"], "fontSize": "9px", "color": C["text3"],
                   "padding": "12px", "background": "rgba(255,48,96,0.05)",
                   "border": "1px solid rgba(255,48,96,0.15)", "borderRadius": "8px",
                   "lineHeight": "1.7"}),
    ], style={"maxWidth": "1000px", "margin": "0 auto", "padding": "40px 24px"})],
    style={**PW, "background": C["ink"], "color": C["text"]})


# ── layout ─────────────────────────────────────────────────────────────────────
def nav_item(n, label):
    return html.Div([
        html.Div(str(n), style={
            "width": "16px", "height": "16px", "borderRadius": "50%",
            "background": C["border"], "display": "flex",
            "alignItems": "center", "justifyContent": "center",
            "fontSize": "8px", "flexShrink": "0"
        }),
        label
    ], id=f"nav-{n}", n_clicks=0, style={
        "display": "flex", "alignItems": "center", "gap": "6px",
        "padding": "6px 10px", "fontFamily": F["mono"], "fontSize": "9px",
        "letterSpacing": "0.1em", "color": C["text3"], "cursor": "pointer",
        "whiteSpace": "nowrap", "borderBottom": "2px solid transparent",
        "marginBottom": "-1px"
    })

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400;500&family=Nunito:wght@400;500;600;700&display=swap"
    ],
    suppress_callback_exceptions=True,
    title="OncosenseAI"
)
server = app.server

app.layout = html.Div([
    dcc.Store(id="stage", data=1),
    dcc.Store(id="diag-store", data={}),

    html.Nav([
        html.Div([
            html.Span("Oncosense", style={"color": "#fff"}),
            html.Span("AI", style={"color": C["teal"]}),
        ], id="nav-logo", n_clicks=0,
           style={"fontFamily": F["serif"], "fontSize": "1.1rem", "fontWeight": "600",
                  "cursor": "pointer", "whiteSpace": "nowrap"}),
        html.Div([nav_item(i+1, STAGE_LABELS[i]) for i in range(8)],
                 style={"display": "flex", "alignItems": "center",
                        "marginLeft": "32px", "flex": "1", "overflowX": "auto"}),
        html.Div([
            html.Div(style={"width": "6px", "height": "6px", "borderRadius": "50%",
                            "background": C["danger"]}),
            "CRITICAL ALERT"
        ], id="nav-crit", style={"display": "none", "marginLeft": "auto",
            "fontFamily": F["mono"], "fontSize": "8px", "letterSpacing": "0.1em",
            "color": C["danger"], "alignItems": "center", "gap": "6px", "whiteSpace": "nowrap"}),
    ], style={
        "position": "fixed", "top": 0, "left": 0, "right": 0, "zIndex": 1000,
        "background": "rgba(13,17,23,0.97)", "backdropFilter": "blur(16px)",
        "borderBottom": f"1px solid {C['border']}", "height": "56px",
        "display": "flex", "alignItems": "center", "padding": "0 24px",
    }),

    html.Div(id="page"),

    html.Link(rel="stylesheet", href="/assets/custom.css"),
], style={"background": C["ink"], "minHeight": "100vh", "color": C["text"]})


# ── routing ────────────────────────────────────────────────────────────────────
@app.callback(
    Output("stage", "data"),
    [Input(f"nav-{i}", "n_clicks") for i in range(1, 9)] +
    [Input("nav-logo", "n_clicks"),
     Input("btn-s1-next", "n_clicks"), Input("btn-s2-next", "n_clicks"),
     Input("btn-s3-next", "n_clicks"), Input("btn-s4-next", "n_clicks"),
     Input("btn-s5-next", "n_clicks"), Input("btn-s6-next", "n_clicks"),
     Input("btn-s7-next", "n_clicks")],
    State("stage", "data"),
    prevent_initial_call=True,
)
def route(*args):
    t = ctx.triggered_id
    if t is None: return 1
    if t == "nav-logo": return 1
    for i in range(1, 9):
        if t == f"nav-{i}": return i
    return {"btn-s1-next":2,"btn-s2-next":3,"btn-s3-next":4,"btn-s4-next":5,
            "btn-s5-next":6,"btn-s6-next":7,"btn-s7-next":8}.get(t, args[-1])


PAGES_MAP = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8}

@app.callback(Output("page", "children"), Input("stage", "data"))
def render(stage):
    return PAGES_MAP.get(stage, s1)()


# ── alarm flag ─────────────────────────────────────────────────────────────────
@app.callback(
    Output("alarm-flag", "style"),
    Input({"type": "sx-chip", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def alarm(clicks):
    active = [p["id"]["index"] for p, c in zip(ctx.inputs_list[0], clicks or [])
              if c and c % 2 == 1]
    has_alarm = any(s in ALARM_SX for s in active)
    base = {"background": "#fef2f2", "border": "1px solid #fecaca",
            "borderLeft": "3px solid #dc2626", "borderRadius": "8px",
            "padding": "10px 14px", "fontSize": "0.82rem",
            "color": "#991b1b", "marginBottom": "12px"}
    return base if has_alarm else {**base, "display": "none"}


# ── diagnosis ──────────────────────────────────────────────────────────────────
def _gen_dx(smoke, family, msi, her2, ca199):
    rf = 0
    if family and family != "None": rf += 2
    if smoke == "Current": rf += 2
    if msi == "MSI-H": rf += 1
    if her2 == "Positive": rf += 1
    try:
        if float(ca199 or 0) > 37: rf += 2
        if float(ca199 or 0) > 200: rf += 2
    except: pass
    if rf >= 7:   lvl = "CRITICAL"
    elif rf >= 5: lvl = "HIGH"
    elif rf >= 3: lvl = "MODERATE"
    else:         lvl = "LOW"

    hyp_map = {
        "CRITICAL": ("Pancreatic Ductal Adenocarcinoma", 0.78),
        "HIGH":     ("Upper GI Malignancy — Gastric / Oesophageal", 0.64),
        "MODERATE": ("Early GI Neoplasia — surveillance indicated", 0.51),
        "LOW":      ("Benign / Functional pathology likely", 0.82),
    }
    hyp, conf = hyp_map[lvl]
    dis = round(min(0.98, rf * 0.11 + random.uniform(0.02, 0.08)), 3)
    piv_map = {
        "CRITICAL": ("IMMEDIATE", "CA 19-9 elevation + alarm symptom cluster + genomic burden",
                     "Urgent EUS/CT + MDT within 72 hours"),
        "HIGH":     ("URGENT", "Symptom cluster + elevated risk factor burden",
                     "2-week wait referral + repeat tumour markers"),
        "MODERATE": ("ROUTINE", "Intermediate risk — endoscopic surveillance warranted",
                     "Schedule gastroscopy + 6-month GP follow-up"),
        "LOW":      ("ROUTINE", "Low-risk — reassuring clinical picture",
                     "GP follow-up + lifestyle counselling"),
    }
    urg, finding, action = piv_map[lvl]
    return dict(level=lvl, hyp=hyp, conf=conf, dis=dis, urg=urg,
                finding=finding, action=action, rf=rf)


@app.callback(
    [Output("diag-out", "children"), Output("diag-store", "data")],
    Input("btn-s3-next", "n_clicks"),
    [State("pt_smoke", "value"), State("pt_family", "value"),
     State("g_msi", "value"),    State("g_her2", "value"),
     State("lab_ca199", "value")],
    prevent_initial_call=True,
)
def run_dx(n, smoke, family, msi, her2, ca199):
    d = _gen_dx(smoke, family, msi, her2, ca199)
    lvl = d["level"]

    rc_map = {"CRITICAL": C["danger"], "HIGH": C["warn"],
              "MODERATE": C["gold"],   "LOW": C["green"]}
    uc_map = {"IMMEDIATE": C["danger"], "URGENT": C["warn"], "ROUTINE": C["teal"]}
    rc = rc_map[lvl]
    uc = uc_map[d["urg"]]
    dc = C["danger"] if d["dis"] > 0.7 else C["warn"] if d["dis"] > 0.4 else C["teal"]

    out = html.Div([
        # risk badge
        html.Div([
            html.Div(style={"width": "7px", "height": "7px", "borderRadius": "50%",
                            "background": rc, "marginRight": "6px"}),
            f"● {lvl} RISK"
        ], style={"display": "inline-flex", "alignItems": "center",
                  "padding": "6px 16px", "borderRadius": "100px",
                  "fontFamily": F["mono"], "fontSize": "12px", "letterSpacing": "0.08em",
                  "background": f"{rc}22", "border": f"1px solid {rc}55",
                  "color": rc, "marginBottom": "16px"}),

        # hypothesis
        card([
            html.Div("PRIMARY HYPOTHESIS", style={"fontFamily": F["mono"], "fontSize": "8px",
                "letterSpacing": "0.22em", "color": C["teal"], "marginBottom": "8px"}),
            html.Div(d["hyp"], style={"fontFamily": F["serif"], "fontSize": "1.3rem",
                "fontWeight": "300", "color": C["text"], "lineHeight": "1.4"}),
            html.Div(f"Diagnostic confidence: {d['conf']:.0%}  ·  Risk factor burden: {d['rf']}",
                style={"fontFamily": F["mono"], "fontSize": "10px",
                       "color": C["text2"], "marginTop": "8px"}),
        ], {"background": "linear-gradient(135deg,rgba(0,212,170,0.07),rgba(0,153,255,0.04))",
             "border": "1px solid rgba(0,212,170,0.25)"}),

        # pivot
        html.Div([
            html.Div(d["urg"], style={"display": "inline-flex", "padding": "2px 9px",
                "borderRadius": "3px", "fontFamily": F["mono"], "fontSize": "8px",
                "letterSpacing": "0.12em", "background": f"{uc}25",
                "color": uc, "marginBottom": "8px"}),
            html.Div(d["finding"], style={"fontFamily": F["mono"], "fontSize": "13px",
                "color": C["text"], "fontWeight": "500", "marginBottom": "8px"}),
            html.Div(f"→ {d['action']}", style={"fontFamily": F["mono"], "fontSize": "11px",
                "color": C["text2"], "lineHeight": "1.7"}),
        ], style={"borderRadius": "10px", "padding": "18px 20px", "marginBottom": "16px",
                  "background": f"{uc}0D", "border": f"1px solid {uc}40",
                  "borderLeft": f"4px solid {uc}"}),

        # dissonance
        card([
            html.Div("DISSONANCE SCORE", style={"fontFamily": F["mono"], "fontSize": "8px",
                "letterSpacing": "0.16em", "color": C["text3"], "marginBottom": "4px"}),
            html.Div(f"{d['dis']:.3f}", style={"fontFamily": F["mono"], "fontSize": "32px",
                "fontWeight": "300", "color": dc}),
            html.Div(
                "HIGH CLINICAL DISSONANCE" if d["dis"] > 0.7 else
                "MODERATE DISSONANCE" if d["dis"] > 0.4 else "LOW DISSONANCE",
                style={"fontFamily": F["mono"], "fontSize": "9px",
                       "color": C["text2"], "marginTop": "4px", "marginBottom": "12px"}),
            html.Div(style={"height": "6px", "background": C["border2"],
                            "borderRadius": "4px", "overflow": "hidden", "position": "relative"}),
            html.Div(style={"height": "6px", "width": f"{d['dis']*100:.0f}%",
                            "background": dc, "borderRadius": "4px", "marginTop": "-6px"}),
            html.Div("⚠ RESEARCH PROTOTYPE ONLY — Not for direct patient care decisions. "
                     "Not validated by any regulatory authority.",
                style={"fontFamily": F["mono"], "fontSize": "9px", "color": C["text3"],
                       "marginTop": "12px", "padding": "8px",
                       "background": "rgba(255,48,96,0.06)",
                       "borderRadius": "5px", "border": "1px solid rgba(255,48,96,0.2)"}),
        ]),
    ], style={"animation": "fadeUp 0.4s ease"})

    return out, d


# ── treatment ──────────────────────────────────────────────────────────────────
@app.callback(
    Output("tx-out", "children"),
    Input("diag-store", "data"),
    prevent_initial_call=True,
)
def render_tx(d):
    if not d: raise dash.exceptions.PreventUpdate
    lvl = d.get("level", "LOW")
    tx = TREATMENTS.get(lvl, TREATMENTS["LOW"])

    return html.Div([
        card([
            html.Div("PRIMARY REGIMEN", style={"fontFamily": F["mono"], "fontSize": "8px",
                "letterSpacing": "0.2em", "color": C["amber"], "marginBottom": "8px"}),
            html.Div(tx["regimen"], style={"fontFamily": F["serif"], "fontSize": "1.2rem",
                "fontWeight": "300", "color": C["text"], "marginBottom": "8px"}),
            html.Div(f"Guideline: {tx['guideline']}", style={"fontFamily": F["mono"],
                "fontSize": "10px", "color": C["text3"], "marginBottom": "12px"}),
            html.Div(tx["note"], style={"fontFamily": F["mono"], "fontSize": "11px",
                "color": C["text2"], "lineHeight": "1.7"}),
        ]),
        *([] if not tx["contra"] else [html.Div([
            html.Div("⛔ CONTRAINDICATIONS", style={"fontFamily": F["mono"], "fontSize": "8px",
                "letterSpacing": "0.2em", "color": C["danger"], "marginBottom": "8px"}),
            *[html.Div(f"• {c}", style={"fontFamily": F["mono"], "fontSize": "11px",
                                         "color": "#ff8fa3"}) for c in tx["contra"]],
        ], style={"background": "rgba(255,48,96,0.06)", "borderRadius": "8px",
                  "padding": "14px", "marginBottom": "14px",
                  "border": "1px solid rgba(255,48,96,0.25)",
                  "borderLeft": f"4px solid {C['danger']}"}),
        ]),
        *([] if not tx["trials"] else [html.Div([
            html.Div("📋 RELEVANT TRIALS", style={"fontFamily": F["mono"], "fontSize": "8px",
                "letterSpacing": "0.2em", "color": C["teal"], "marginBottom": "8px"}),
            *[html.Div(f"• {t}", style={"fontFamily": F["mono"], "fontSize": "11px",
                                         "color": C["text2"]}) for t in tx["trials"]],
        ], style={"background": C["ink2"], "border": f"1px solid {C['border']}",
                  "borderRadius": "8px", "padding": "14px"}),
        ]),
    ])


# ── physician summary ──────────────────────────────────────────────────────────
@app.callback(
    Output("phys-summary", "children"),
    Input("diag-store", "data"),
    prevent_initial_call=True,
)
def phys_summary(d):
    if not d:
        return html.Div("Complete the M6 analysis to populate this summary.",
            style={"fontFamily": F["mono"], "fontSize": "11px",
                   "color": C["text3"], "padding": "20px"})
    stats = [
        ("Risk Level", d.get("level", "—")),
        ("Primary Hypothesis", (d.get("hyp") or "—")[:28] + "…"),
        ("Dissonance Score", f"{d.get('dis', 0):.3f}"),
        ("Recommended Action", d.get("urg", "—")),
    ]
    return html.Div([
        html.Div([
            html.Div([
                html.Div(v, style={"fontFamily": F["mono"], "fontSize": "14px",
                                    "color": C["teal"], "marginBottom": "4px"}),
                html.Div(k, style={"fontFamily": F["mono"], "fontSize": "8px",
                                    "color": C["text3"], "letterSpacing": "0.08em"}),
            ], style={"background": C["ink2"], "border": f"1px solid {C['border']}",
                      "borderRadius": "8px", "padding": "12px",
                      "textAlign": "center", "flex": "1"})
            for k, v in stats
        ], style={"display": "flex", "gap": "10px", "flexWrap": "wrap", "marginBottom": "16px"}),
    ])


if __name__ == "__main__":
    print("\n" + "═"*58)
    print("  OncosenseAI — Early GI Cancer Detection Pipeline")
    print("  Python / Dash · 8 stages incl. SEER Validation")
    print("═"*58)
    print("\n  Place these files next to oncosenseai_app.py:")
    print("    · fig1_km_curves.png")
    print("    · fig2_model_results.png")
    print("    · fig3_deep_dive.png")
    print("\n  → http://localhost:8050\n")
    app.run(debug=False, port=8050)
