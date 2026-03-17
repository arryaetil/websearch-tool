
Copy

import streamlit as st
import json
from datetime import datetime
from researcher import run_research
from pdf_export import generate_pdf
 
st.set_page_config(
    page_title="KYCx · Adverse Media Check",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    [data-testid="stSidebar"] { background: #020c1b; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] input { background: #0a1628 !important; border: 1px solid #1a4a8a !important; color: white !important; border-radius: 6px !important; }
    [data-testid="stSidebar"] .stTextInput label { color: #4a9eff !important; font-size: 0.75rem !important; letter-spacing: 0.05em; text-transform: uppercase; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .kycx-header {
        background: linear-gradient(135deg, #050d1f 0%, #091628 40%, #0d1f3c 100%);
        border-radius: 12px;
        padding: 1.2rem 2rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #0d3060;
        box-shadow: 0 4px 24px rgba(0,100,255,0.08);
    }
    .gdpr-notice {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        font-size: 0.82rem;
        color: #78350f;
        margin-bottom: 1.25rem;
    }
    .review-banner {
        background: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 10px;
        padding: 0.9rem 1.2rem;
        font-size: 0.85rem;
        color: #0c4a6e;
        margin-bottom: 1.25rem;
    }
    .score-wrap {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .score-num { font-size: 3rem; font-weight: 800; line-height: 1; }
    .score-label { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px; }
    .score-verdict { font-size: 1rem; font-weight: 700; margin-bottom: 4px; }
    .score-reason { font-size: 0.83rem; color: #64748b; }
    .section-header {
        font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 0.6rem;
        padding-bottom: 0.4rem; border-bottom: 1px solid #f1f5f9;
    }
    .data-item { padding: 0.6rem 0; border-bottom: 1px solid #f8fafc; font-size: 0.85rem; }
    .data-item:last-child { border-bottom: none; }
    .data-item .di-title { font-weight: 600; color: #1e293b; }
    .data-item .di-sub { color: #64748b; font-size: 0.78rem; margin-top: 2px; }
    .data-item .di-url { color: #1a6eff; font-size: 0.75rem; font-family: monospace; margin-top: 2px; }
    .empty-state { color: #cbd5e1; font-size: 0.82rem; font-style: italic; padding: 0.4rem 0; }
    .flag-high   { background:#fef2f2; border-left:3px solid #ef4444; border-radius:0 6px 6px 0; padding:0.6rem 0.9rem; margin:4px 0; font-size:0.82rem; }
    .flag-medium { background:#fffbeb; border-left:3px solid #f59e0b; border-radius:0 6px 6px 0; padding:0.6rem 0.9rem; margin:4px 0; font-size:0.82rem; }
    .flag-low    { background:#f0fdf4; border-left:3px solid #22c55e; border-radius:0 6px 6px 0; padding:0.6rem 0.9rem; margin:4px 0; font-size:0.82rem; }
    .flag-sev    { font-weight: 700; font-size: 0.72rem; letter-spacing: 0.06em; }
    .flag-high .flag-sev { color: #dc2626; }
    .flag-medium .flag-sev { color: #d97706; }
    .flag-low .flag-sev { color: #16a34a; }
    .conf-bar-bg { background: #f1f5f9; border-radius: 99px; height: 6px; margin-top: 8px; overflow: hidden; }
    .conf-bar-fill { height: 100%; border-radius: 99px; }
    .var-pill {
        display: inline-block; background: #eff6ff; color: #1a6eff;
        border: 1px solid #bfdbfe; border-radius: 99px;
        padding: 2px 10px; font-size: 0.75rem; margin: 2px 3px; font-family: monospace;
    }
    .stTextInput input { border-radius: 8px !important; border: 1px solid #e2e8f0 !important; font-size: 0.88rem !important; }
    .stTextInput input:focus { border-color: #1a6eff !important; box-shadow: 0 0 0 3px rgba(26,110,255,0.1) !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0a3d8f 0%, #1a6eff 100%) !important;
        border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; letter-spacing: 0.02em !important;
        padding: 0.6rem 1.5rem !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(26,110,255,0.4) !important;
    }
    hr { border-color: #f1f5f9 !important; }
</style>
""", unsafe_allow_html=True)
 
# ── Sidebar
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:0 0 1.2rem 0;border-bottom:1px solid #0d3060;margin-bottom:1.2rem;text-align:center'>
        <div style='font-family:Georgia,serif;font-size:2rem;font-weight:700;color:white;letter-spacing:.05em'>KYC<span style='color:#4a9eff'>X</span></div>
        <div style='font-size:0.7rem;color:#4a7ab5;letter-spacing:.12em;text-transform:uppercase;margin-top:2px'>Adverse Media Check</div>
    </div>
    """, unsafe_allow_html=True)
    api_key = st.text_input("OpenAI API Key", type="password")
 
    st.markdown("""
    <div style='margin-top:1.5rem;padding-top:1rem;border-top:1px solid #1e4a70'>
        <div style='font-size:0.7rem;color:#64a0c8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem'>System</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.78rem;color:#94b8d8'>🤖 Model: gpt-5 + web search</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.78rem;color:#94b8d8;margin-top:4px'>🔍 Dual-pass research</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.78rem;color:#94b8d8;margin-top:4px'>📋 Structured JSON output</div>", unsafe_allow_html=True)
 
    st.markdown("""
    <div style='margin-top:1.5rem;padding:0.75rem;background:#0a3d1f;border-radius:8px;border:1px solid #166534'>
        <div style='font-size:0.72rem;font-weight:700;color:#4ade80;margin-bottom:3px'>● EU GDPR Compliant</div>
        <div style='font-size:0.7rem;color:#86efac'>Audit log active<br>Human review required</div>
    </div>
    """, unsafe_allow_html=True)
 
# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="kycx-header">
    <div>
        <div style="font-size:0.85rem;font-weight:700;color:#4a9eff;letter-spacing:.1em;text-transform:uppercase">Adverse Media Check</div>
        <div style="font-size:0.75rem;color:#4a7ab5;margin-top:3px">AI-powered KYC screening · Dual-pass web intelligence</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px">
        <span style="width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block"></span>
        <span style="font-size:0.78rem;color:#4a9eff">System online</span>
    </div>
</div>
""", unsafe_allow_html=True)
 
# ── GDPR notice ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="gdpr-notice">
⚠️ <strong>GDPR / AVG:</strong> This tool aggregates publicly available information only,
for legitimate compliance purposes. All results require human analyst review.
All searches are logged. Do not use without a valid legal basis.
</div>
""", unsafe_allow_html=True)
 
# ── Input form ────────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="section-header">Subject Information</div>', unsafe_allow_html=True)
 
    col1, col2 = st.columns(2)
    with col1:
        full_name   = st.text_input("Full name *", placeholder="Jan de Vries")
        city_region = st.text_input("City / Region *", placeholder="Amsterdam, Netherlands")
    with col2:
        age         = st.text_input("Age (optional)", placeholder="42")
        employer    = st.text_input("Employer (optional)", placeholder="ING Bank")
 
    context     = st.text_input("Research context (optional)", placeholder="Mortgage application · €450,000")
    analyst_name= st.text_input("Analyst name (audit log)", placeholder="Your name")
 
    run_btn = st.button("🔍 Run Identity Research", type="primary", use_container_width=True)
 
# ── Run research ──────────────────────────────────────────────────────────────
if run_btn:
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
        st.stop()
    if not full_name or not city_region:
        st.error("Full name and city/region are required.")
        st.stop()
 
    with st.status("Running dual-pass research...", expanded=True) as status:
        st.write("🔎 Pass 1 — Identity & professional background...")
        st.write("📰 Pass 2 — Adverse media & risk indicators...")
        result, error = run_research(
            api_key=api_key,
            name=full_name,
            city=city_region,
            age=age,
            employer=employer,
            context=context
        )
        if error:
            status.update(label=f"Error: {error}", state="error")
            st.stop()
        status.update(label="Research complete!", state="complete")
 
    # Audit log
    with open("audit_log.jsonl", "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "analyst": analyst_name or "unknown",
            "subject_name": full_name,
            "subject_city": city_region,
            "context": context
        }) + "\n")
 
    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="review-banner">
        👁 <strong>Human review required.</strong>
        This report was generated by AI from public sources only.
        A qualified analyst must review all findings before any decision is made.
    </div>
    """, unsafe_allow_html=True)
 
    # Title row
    col_title, col_meta = st.columns([3, 2])
    with col_title:
        st.markdown(f"### {full_name} · {city_region}")
    with col_meta:
        st.markdown(f"<div style='text-align:right;color:#94a3b8;font-size:0.78rem;padding-top:8px'>"
                    f"Generated {datetime.now().strftime('%d %b %Y %H:%M')} · Analyst: {analyst_name or '—'}</div>",
                    unsafe_allow_html=True)
 
    # Confidence score
    score   = int(result.get("confidence_score", 0))
    verdict = result.get("confidence_verdict", "Low")
    reason  = result.get("confidence_reasoning", "")
    color   = "#22c55e" if score >= 75 else "#f59e0b" if score >= 45 else "#ef4444"
 
    st.markdown(f"""
    <div class="score-wrap">
        <div>
            <div class="score-num" style="color:{color}">{score}</div>
            <div class="score-label">/ 100</div>
        </div>
        <div style="flex:1">
            <div class="score-verdict" style="color:{color}">{verdict} Confidence</div>
            <div class="score-reason">{reason}</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{score}%;background:{color}"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
 
    # Name variations
    variations = result.get("name_variations_searched", [])
    if variations:
        pills = "".join(f'<span class="var-pill">{v}</span>' for v in variations)
        st.markdown(f"<div style='margin-bottom:1rem'><span style='font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;font-weight:700'>Searched variations</span><br/><div style='margin-top:6px'>{pills}</div></div>", unsafe_allow_html=True)
 
    # Two column layout
    col_l, col_r = st.columns(2)
 
    def data_items(items, title_key, sub_keys, url_key=None):
        if not items:
            return '<div class="empty-state">Insufficient data</div>'
        html = ""
        for item in items:
            title = item.get(title_key, "—")
            subs  = " · ".join(str(item.get(k,"")) for k in sub_keys if item.get(k))
            url   = item.get(url_key, "") if url_key else ""
            html += f'<div class="data-item"><div class="di-title">{title}</div>'
            if subs: html += f'<div class="di-sub">{subs}</div>'
            if url:  html += f'<div class="di-url">{url[:60]}{"…" if len(url)>60 else ""}</div>'
            html += '</div>'
        return html
 
    with col_l:
        st.markdown('<div class="section-header">👤 Identity matches</div>', unsafe_allow_html=True)
        st.markdown(data_items(result.get("identity_matches",[]),
                               "name", ["description", "confidence"]), unsafe_allow_html=True)
 
        st.markdown('<div class="section-header" style="margin-top:1.2rem">💼 Professional profiles</div>', unsafe_allow_html=True)
        st.markdown(data_items(result.get("professional_profiles",[]),
                               "role", ["company", "platform"], "url_hint"), unsafe_allow_html=True)
 
        st.markdown('<div class="section-header" style="margin-top:1.2rem">🏢 Business records</div>', unsafe_allow_html=True)
        st.markdown(data_items(result.get("business_records",[]),
                               "entity", ["role", "status"], "source"), unsafe_allow_html=True)
 
    with col_r:
        st.markdown('<div class="section-header">📰 Media mentions</div>', unsafe_allow_html=True)
        media = result.get("media_mentions", [])
        if media:
            for m in media:
                icon = {"positive":"🟢","neutral":"⚪","negative":"🔴"}.get(m.get("sentiment",""), "⚪")
                st.markdown(
                    f'<div class="data-item">'
                    f'<div class="di-title">{icon} {m.get("title","")}</div>'
                    f'<div class="di-sub">{m.get("source","")} · {m.get("date","")} · {m.get("sentiment","")}</div>'
                    f'<div class="di-sub">{m.get("summary","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="empty-state">Insufficient data</div>', unsafe_allow_html=True)
 
        st.markdown('<div class="section-header" style="margin-top:1.2rem">🌐 Social media</div>', unsafe_allow_html=True)
        st.markdown(data_items(result.get("social_media_presence",[]),
                               "platform", ["description"]), unsafe_allow_html=True)
 
    # Risk flags full width
    st.markdown('<div class="section-header" style="margin-top:1.2rem">🚨 Risk flags</div>', unsafe_allow_html=True)
    flags = result.get("risk_flags", [])
    if not flags:
        st.success("✓ No risk flags identified.")
    else:
        for f in flags:
            sev  = f.get("severity","low").lower()
            icon = {"high":"⛔","medium":"⚠️","low":"ℹ️"}.get(sev,"ℹ️")
            st.markdown(
                f'<div class="flag-{sev}">'
                f'<span class="flag-sev">{icon} [{sev.upper()}] {f.get("category","")}</span>'
                f'<div style="margin-top:3px;color:#374151">{f.get("description","")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
 
    # Sources
    st.markdown('<div class="section-header" style="margin-top:1.2rem">🔗 Sources</div>', unsafe_allow_html=True)
    sources = result.get("sources", [])
    if sources:
        for s in sources:
            url  = s.get("url","#")
            name = s.get("name", url)
            stype= s.get("type","")
            st.markdown(
                f'<div style="font-size:0.82rem;padding:3px 0">'
                f'<a href="{url}" target="_blank" style="color:#3b82f6">{name}</a>'
                f' <span style="background:#f1f5f9;color:#64748b;font-size:0.72rem;'
                f'padding:1px 7px;border-radius:99px;margin-left:6px">{stype}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div class="empty-state">No sources recorded.</div>', unsafe_allow_html=True)
 
    # Export buttons
    st.divider()
    col_pdf, col_json = st.columns(2)
 
    with col_pdf:
        try:
            pdf_bytes = generate_pdf(result, full_name, city_region, analyst_name)
            st.download_button(
                label="⬇️ Download PDF rapport",
                data=pdf_bytes,
                file_name=f"rapport_{full_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.warning(f"PDF generatie mislukt: {e}")
 
    with col_json:
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name=f"report_{full_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )
 
    with st.expander("📄 Raw JSON bekijken"):
        st.json(result)