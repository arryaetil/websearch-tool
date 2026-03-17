import streamlit as st
import json
from datetime import datetime
from researcher import run_research
from pdf_export import generate_pdf

st.set_page_config(
    page_title="KYCX · Adverse Media Check",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg: #07111f;
    --panel: #0b1728;
    --panel-2: #0f1d33;
    --panel-3: #13233d;
    --line: #1f3354;
    --line-soft: #172844;
    --text: #e8eef9;
    --muted: #8ea3c5;
    --muted-2: #6f85a8;
    --blue: #2f80ff;
    --blue-2: #1b64d8;
    --green: #16c784;
    --yellow: #f59e0b;
    --red: #ef4444;
    --card-shadow: 0 10px 30px rgba(0,0,0,0.28);
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top right, rgba(47,128,255,0.14), transparent 30%),
        radial-gradient(circle at top left, rgba(22,199,132,0.06), transparent 22%),
        linear-gradient(180deg, #06101d 0%, #081321 100%) !important;
    color: var(--text);
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2.5rem;
    max-width: 1400px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #03101d 0%, #061425 100%);
    border-right: 1px solid #0f2440;
}
[data-testid="stSidebar"] * {
    color: #dbe7fb !important;
}
[data-testid="stSidebar"] input {
    background: #0a1729 !important;
    border: 1px solid #234168 !important;
    color: white !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] .stTextInput label {
    color: #8bb7ff !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.02) !important;
    color: white !important;
    border: 1px solid #2b3d59 !important;
    border-radius: 12px !important;
    font-size: 0.93rem !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #2f80ff !important;
    box-shadow: 0 0 0 3px rgba(47,128,255,0.14) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #194ea8 0%, #2f80ff 100%) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 14px !important;
    color: white !important;
    font-weight: 700 !important;
    min-height: 54px !important;
    font-size: 1rem !important;
    box-shadow: 0 10px 24px rgba(47,128,255,0.22) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 12px 28px rgba(47,128,255,0.3) !important;
}

.stDownloadButton > button {
    border-radius: 12px !important;
    min-height: 48px !important;
    border: 1px solid #27426c !important;
    background: #0d1a2e !important;
    color: #e8eef9 !important;
    font-weight: 600 !important;
}

div[data-testid="stExpander"] {
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    background: rgba(12,22,37,0.88) !important;
}

.kycx-header {
    background:
        radial-gradient(circle at top right, rgba(47,128,255,0.18), transparent 36%),
        linear-gradient(135deg, rgba(9,24,43,0.98) 0%, rgba(11,24,43,0.98) 100%);
    border: 1px solid #1b3356;
    border-radius: 20px;
    padding: 1.35rem 1.6rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: var(--card-shadow);
}

.hero-title {
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #61a5ff;
}
.hero-sub {
    font-size: 0.95rem;
    color: #89a6cf;
    margin-top: 6px;
}

.top-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border: 1px solid #1c3d66;
    background: rgba(14,31,54,0.78);
    color: #b8d5ff;
    border-radius: 999px;
    padding: 7px 12px;
    font-size: 0.8rem;
    font-weight: 600;
}

.notice {
    border-radius: 16px;
    padding: 1rem 1.15rem;
    margin-bottom: 1rem;
    border: 1px solid;
    box-shadow: var(--card-shadow);
}
.notice.warn {
    background: linear-gradient(135deg, rgba(245,158,11,0.10), rgba(245,158,11,0.04));
    border-color: rgba(245,158,11,0.34);
    color: #ffe4b2;
}
.notice.info {
    background: linear-gradient(135deg, rgba(47,128,255,0.10), rgba(47,128,255,0.04));
    border-color: rgba(47,128,255,0.28);
    color: #dbeafe;
}

.section-header {
    font-size: 0.76rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #95afd3;
    margin: 0.2rem 0 0.7rem 0;
    padding-bottom: 0.45rem;
    border-bottom: 1px solid var(--line-soft);
}

.glass-card {
    background: linear-gradient(180deg, rgba(12,22,37,0.92), rgba(10,19,32,0.92));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1rem 1rem;
    box-shadow: var(--card-shadow);
}

.score-wrap {
    background: linear-gradient(180deg, rgba(14,24,40,0.98), rgba(10,18,31,0.98));
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 1.2rem 1.25rem;
    display: flex;
    align-items: center;
    gap: 1.1rem;
    margin-bottom: 1rem;
    box-shadow: var(--card-shadow);
}
.score-num {
    font-size: 3.4rem;
    font-weight: 800;
    line-height: 1;
}
.score-label {
    font-size: 0.72rem;
    color: #8198bc;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.score-verdict {
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 4px;
}
.score-reason {
    font-size: 0.84rem;
    color: #91a5c6;
}
.conf-bar-bg {
    background: #13243f;
    border-radius: 999px;
    height: 8px;
    margin-top: 10px;
    overflow: hidden;
    border: 1px solid #193153;
}
.conf-bar-fill {
    height: 100%;
    border-radius: 999px;
}

.kpi-chip {
    display: inline-block;
    background: rgba(47,128,255,0.10);
    border: 1px solid rgba(47,128,255,0.24);
    color: #8fc1ff;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.75rem;
    margin: 3px 5px 0 0;
    font-family: monospace;
}

.data-item {
    padding: 0.72rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.88rem;
}
.data-item:last-child { border-bottom: none; }

.di-title {
    font-weight: 700;
    color: #edf3ff;
}
.di-sub {
    color: #8aa0c4;
    font-size: 0.79rem;
    margin-top: 3px;
    line-height: 1.45;
}
.di-url {
    color: #6fb1ff;
    font-size: 0.74rem;
    font-family: monospace;
    margin-top: 4px;
    word-break: break-all;
}

.empty-state {
    color: #7087ac;
    font-size: 0.84rem;
    font-style: italic;
    padding: 0.5rem 0;
}

.flag-box {
    border-radius: 14px;
    padding: 0.85rem 0.95rem;
    margin-bottom: 0.6rem;
    border: 1px solid;
}
.flag-high {
    background: rgba(239,68,68,0.09);
    border-color: rgba(239,68,68,0.24);
}
.flag-medium {
    background: rgba(245,158,11,0.09);
    border-color: rgba(245,158,11,0.24);
}
.flag-low {
    background: rgba(34,197,94,0.08);
    border-color: rgba(34,197,94,0.22);
}
.flag-head {
    font-size: 0.76rem;
    letter-spacing: 0.08em;
    font-weight: 800;
    margin-bottom: 4px;
}
.flag-high .flag-head { color: #ff8c8c; }
.flag-medium .flag-head { color: #ffd27b; }
.flag-low .flag-head { color: #7ee0ad; }

.source-link {
    display: block;
    text-decoration: none;
    border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.55rem;
    transition: 0.18s ease;
}
.source-link:hover {
    border-color: rgba(47,128,255,0.34);
    background: rgba(47,128,255,0.05);
}
.source-title {
    color: #dbeafe;
    font-size: 0.86rem;
    font-weight: 700;
}
.source-url {
    color: #7fa6dc;
    font-size: 0.73rem;
    margin-top: 2px;
    word-break: break-all;
}
.source-tag {
    display: inline-block;
    margin-top: 8px;
    background: rgba(47,128,255,0.10);
    color: #9fc8ff;
    border: 1px solid rgba(47,128,255,0.22);
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 0.7rem;
}

.report-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: white;
    margin-top: 0.2rem;
}
.report-meta {
    text-align: right;
    color: #7c92b8;
    font-size: 0.78rem;
    padding-top: 10px;
}

.subtle-divider {
    height: 1px;
    width: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    margin: 1.2rem 0 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:0.2rem 0 1.3rem 0;border-bottom:1px solid #113157;margin-bottom:1.15rem;text-align:center'>
        <div style='font-family:Georgia,serif;font-size:2.05rem;font-weight:700;color:white;letter-spacing:.04em'>KYC<span style='color:#62a8ff'>X</span></div>
        <div style='font-size:0.72rem;color:#79a9df;letter-spacing:.14em;text-transform:uppercase;margin-top:2px'>Adverse Media Check</div>
    </div>
    """, unsafe_allow_html=True)

    api_key = st.text_input("OpenAI API Key", type="password")

    st.markdown("""
    <div style='margin-top:1.45rem;padding-top:1rem;border-top:1px solid #153153'>
        <div style='font-size:0.72rem;color:#7cb3ff;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.65rem'>System</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.8rem;color:#cfe0fb'>🤖 Model: GPT-powered research</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.8rem;color:#cfe0fb;margin-top:5px'>🌐 Web intelligence enabled</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.8rem;color:#cfe0fb;margin-top:5px'>📋 Structured JSON output</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.8rem;color:#cfe0fb;margin-top:5px'>⚖️ Human review workflow</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='margin-top:1.4rem;padding:0.9rem;background:linear-gradient(135deg,rgba(22,199,132,0.18),rgba(22,199,132,0.10));border-radius:14px;border:1px solid rgba(22,199,132,0.28)'>
        <div style='font-size:0.74rem;font-weight:800;color:#9df0c8;margin-bottom:5px'>● EU GDPR Aware</div>
        <div style='font-size:0.74rem;color:#d6ffea;line-height:1.5'>
            Audit log active<br>
            Human review required<br>
            Public-source only
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="kycx-header">
    <div>
        <div class="hero-title">Adverse Media Check</div>
        <div class="hero-sub">AI-powered KYC screening · public-source intelligence · analyst review workflow</div>
    </div>
    <div class="top-pill">
        <span style="width:8px;height:8px;border-radius:50%;background:#16c784;display:inline-block"></span>
        System online
    </div>
</div>
""", unsafe_allow_html=True)

# ── Notices ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="notice warn">
⚠️ <strong>GDPR / AVG:</strong> This tool aggregates publicly available information only for legitimate compliance use.
All results require human analyst review. Do not use without a valid legal basis.
</div>
""", unsafe_allow_html=True)

# ── Input form ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Subject Information</div>', unsafe_allow_html=True)

with st.container():
    c1, c2 = st.columns(2)
    with c1:
        full_name = st.text_input("Full name *", placeholder="Albert Bril")
        city_region = st.text_input("City / Region *", placeholder="Bergentheim")
        context = st.text_input("Research context (optional)", placeholder="Mortgage application · €450,000")
    with c2:
        age = st.text_input("Age (optional)", placeholder="42")
        employer = st.text_input("Employer (optional)", placeholder="ING Bank")
        analyst_name = st.text_input("Analyst name (audit log)", placeholder="Your name")

    run_btn = st.button("🔎 Run Identity Research", type="primary", use_container_width=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def render_data_items(items, title_key, sub_keys=None, url_key=None):
    if not items:
        return '<div class="empty-state">Insufficient data</div>'

    sub_keys = sub_keys or []
    html = ""
    for item in items:
        title = item.get(title_key, "—")
        subs = " · ".join(str(item.get(k, "")) for k in sub_keys if item.get(k))
        url = item.get(url_key, "") if url_key else ""

        html += '<div class="data-item">'
        html += f'<div class="di-title">{title}</div>'
        if subs:
            html += f'<div class="di-sub">{subs}</div>'
        if url:
            html += f'<div class="di-url">{url}</div>'
        html += '</div>'
    return html

def verdict_color(score: int) -> str:
    if score >= 80:
        return "#16c784"
    if score >= 55:
        return "#f59e0b"
    return "#ef4444"

# ── Run research ──────────────────────────────────────────────────────────────
if run_btn:
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
        st.stop()

    if not full_name or not city_region:
        st.error("Full name and city/region are required.")
        st.stop()

    with st.status("Running public-source research...", expanded=True) as status:
        st.write("🔎 Identity resolution and profile matching...")
        st.write("🏢 Professional, business, and public records...")
        st.write("📰 Media and legal/adverse public records...")
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

    with open("audit_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "analyst": analyst_name or "unknown",
            "subject_name": full_name,
            "subject_city": city_region,
            "context": context
        }, ensure_ascii=False) + "\\n")

    st.markdown("""
    <div class="notice info">
        👁 <strong>Human review required.</strong>
        This report was generated from public sources only. A qualified analyst must review all findings before any decision is made.
    </div>
    """, unsafe_allow_html=True)

    # ── Title row ─────────────────────────────────────────────────────────────
    t1, t2 = st.columns([3, 2])
    with t1:
        st.markdown(f'<div class="report-title">{full_name} <span style="color:#7d99c6">·</span> {city_region}</div>', unsafe_allow_html=True)
    with t2:
        st.markdown(
            f'<div class="report-meta">Generated {datetime.now().strftime("%d %b %Y %H:%M")} · Analyst: {analyst_name or "—"}</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="subtle-divider"></div>', unsafe_allow_html=True)

    # ── Confidence ────────────────────────────────────────────────────────────
    score = int(result.get("confidence_score", 0))
    verdict = result.get("confidence_verdict", "Low")
    reasoning = result.get("confidence_reasoning", "")
    color = verdict_color(score)

    st.markdown(f"""
    <div class="score-wrap">
        <div>
            <div class="score-num" style="color:{color}">{score}</div>
            <div class="score-label">/ 100 confidence</div>
        </div>
        <div style="flex:1">
            <div class="score-verdict" style="color:{color}">{verdict} Confidence</div>
            <div class="score-reason">{reasoning}</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{score}%;background:{color}"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Variations ────────────────────────────────────────────────────────────
    variations = result.get("name_variations_searched", [])
    if variations:
        chips = "".join([f'<span class="kpi-chip">{v}</span>' for v in variations])
        st.markdown(
            f"<div style='margin-bottom:1rem'><div class='section-header' style='margin-bottom:0.4rem'>Searched Variations</div>{chips}</div>",
            unsafe_allow_html=True
        )

    # ── Grid layout ───────────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">👤 Identity Matches</div>', unsafe_allow_html=True)
        st.markdown(
            render_data_items(result.get("identity_matches", []), "name", ["description", "confidence"]),
            unsafe_allow_html=True
        )

        st.markdown('<div class="section-header" style="margin-top:1rem">💼 Professional Profiles</div>', unsafe_allow_html=True)
        st.markdown(
            render_data_items(result.get("professional_profiles", []), "role", ["company", "platform"], "url_hint"),
            unsafe_allow_html=True
        )

        st.markdown('<div class="section-header" style="margin-top:1rem">🏢 Business Records</div>', unsafe_allow_html=True)
        st.markdown(
            render_data_items(result.get("business_records", []), "entity", ["role", "status"], "source"),
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">📰 Media Mentions</div>', unsafe_allow_html=True)

        media = result.get("media_mentions", [])
        if media:
            for m in media:
                sentiment = (m.get("sentiment") or "").lower()
                icon = {"positive": "🟢", "neutral": "⚪", "negative": "🔴"}.get(sentiment, "⚪")
                st.markdown(
                    f"""
                    <div class="data-item">
                        <div class="di-title">{icon} {m.get("title", "—")}</div>
                        <div class="di-sub">{m.get("source", "")} · {m.get("date", "")} · {m.get("sentiment", "")}</div>
                        <div class="di-sub">{m.get("summary", "")}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="empty-state">Insufficient data</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header" style="margin-top:1rem">🌐 Social Media Presence</div>', unsafe_allow_html=True)
        st.markdown(
            render_data_items(result.get("social_media_presence", []), "platform", ["description"]),
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Legal records ─────────────────────────────────────────────────────────
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">⚖️ Legal Public Records</div>', unsafe_allow_html=True)
    st.markdown(
        render_data_items(result.get("legal_public_records", []), "issue_type", ["date", "summary"], "source"),
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Risk flags ────────────────────────────────────────────────────────────
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🚨 Risk Flags</div>', unsafe_allow_html=True)

    flags = result.get("risk_flags", [])
    if not flags:
        st.success("✓ No risk flags identified.")
    else:
        for f in flags:
            sev = (f.get("severity") or "low").lower()
            box_class = "flag-high" if sev == "high" else "flag-medium" if sev == "medium" else "flag-low"
            icon = "⛔" if sev == "high" else "⚠️" if sev == "medium" else "ℹ️"
            st.markdown(
                f"""
                <div class="flag-box {box_class}">
                    <div class="flag-head">{icon} [{sev.upper()}] {f.get("category", "")}</div>
                    <div class="di-sub" style="font-size:0.83rem;color:#d7e5fb">{f.get("description", "")}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Sources ───────────────────────────────────────────────────────────────
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🔗 Sources</div>', unsafe_allow_html=True)

    sources = result.get("sources", [])
    if sources:
        for s in sources:
            url = s.get("url", "#")
            name = s.get("name", url)
            stype = s.get("type", "web")
            st.markdown(
                f"""
                <a class="source-link" href="{url}" target="_blank">
                    <div class="source-title">{name}</div>
                    <div class="source-url">{url}</div>
                    <span class="source-tag">{stype}</span>
                </a>
                """,
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div class="empty-state">No sources recorded.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────
    st.divider()
    ex1, ex2 = st.columns(2)

    with ex1:
        try:
            pdf_bytes = generate_pdf(result, full_name, city_region, analyst_name)
            st.download_button(
                label="⬇️ Download PDF report",
                data=pdf_bytes,
                file_name=f"report_{full_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.warning(f"PDF generation failed: {e}")

    with ex2:
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name=f"report_{full_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )

    with st.expander("📄 View raw JSON"):
        st.json(result)