import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. APP CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="centered")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #004aad; color: white; font-weight: bold; }
        .stSelectbox, .stTextInput, .stMultiselect { border-radius: 8px; }
        h1 { color: #004aad; }
        .card { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eee; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADERS
# ─────────────────────────────────────────────
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        idx = xls.parse(xls.sheet_names[0])
        return xls, dict(zip(idx.iloc[:,0], idx.iloc[:,1]))
    except:
        st.error("Missing: University Readiness_new.xlsx")
        st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, dict(zip(idx.iloc[:,0], idx.iloc[:,1]))
    except:
        st.error("Missing: Benchmarking_USA.xlsx")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF ENGINE (Gap Analysis + Curation)
# ─────────────────────────────────────────────
def generate_pdf(name, student_class, course, total_score, responses, bench_df, q_benchmarks, countries, counsellor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('T', parent=styles['Title'], textColor=colors.HexColor("#004aad"), spaceAfter=20)
    h_style = ParagraphStyle('H', parent=styles['Heading2'], textColor=colors.HexColor("#333333"), spaceBefore=10)
    
    elements = []

    # Logo
    try:
        img = Image("Uppseekers Logo.png", width=140, height=42)
        img.hAlign = 'LEFT'
        elements.append(img)
        elements.append(Spacer(1, 15))
    except: pass

    elements.append(Paragraph(f"Admit AI Profile Report", title_style))
    elements.append(Paragraph(f"<b>Student:</b> {name} | <b>Class:</b> {student_class}", styles['Normal']))
    elements.append(Paragraph(f"<b>Interested Course:</b> {course}", styles['Normal']))
    elements.append(Paragraph(f"<b>Preferred Regions:</b> {', '.join(countries)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Overall Profile Strength: {round(total_score, 1)}", h_style))
    elements.append(Spacer(1, 10))

    # SECTION 1: Question-wise Gap
    elements.append(Paragraph("1. Question-wise Improvement Scope", styles['Heading3']))
    q_data = [["Section", "Student", "Ideal", "Gap/Scope"]]
    for i, (q_text, ans, score) in enumerate(responses):
        ideal = q_benchmarks.get(f"Q{i+1}", 0)
        gap = round(ideal - score, 1)
        scope = f"+{gap} pts needed" if gap > 0 else "Benchmark Met ✅"
        q_data.append([Paragraph(q_text, styles['Normal']), str(score), str(round(ideal, 1)), Paragraph(scope, styles['Normal'])])
    
    qt = Table(q_data, colWidths=[200, 60, 60, 130])
    qt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004aad")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(qt)
    elements.append(Spacer(1, 25))

    # SECTION 2: Curated University Fit
    elements.append(Paragraph("2. Curated University Recommendations", styles['Heading3']))
    
    def add_bucket(df, title, color, limit):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            u_data = [["University", "Target Score", "Match Gap"]]
            for _, row in df.sort_values("Score Gap %", ascending=False).head(limit).iterrows():
                u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
            ut = Table(u_data, colWidths=[300, 80, 70])
            ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
            elements.append(ut)
            elements.append(Spacer(1, 12))

    # Gap Logic
    safe = bench_df[bench_df["Score Gap %"] >= 0]
    target = bench_df[(bench_df["Score Gap %"] <= -10) & (bench_df["Score Gap %"] >= -20)]
    dream = bench_df[bench_df["Score Gap %"] < -20]

    add_bucket(safe, "🟢 SAFE UNIVERSITIES (Top 5)", colors.darkgreen, 5)
    add_bucket(target, "🟡 TARGET UNIVERSITIES (Top 5)", colors.orange, 5)
    add_bucket(dream, "🔴 DREAM UNIVERSITIES (Top 5)", colors.red, 5)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. STREAMLIT APP FLOW
# ─────────────────────────────────────────────
apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'

# PAGE: INTRO
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    st.markdown("### Profile Analysis & University Matchmaking")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        c1, c2 = st.columns(2)
        with c1: s_class = st.selectbox("Current Class", ["9", "10", "11", "12"])
        with c2: city = st.text_input("City")
        
        country_list = ["USA", "UK", "Canada", "Australia", "Germany", "Singapore", "Netherlands", "France", "Switzerland"]
        pref_countries = st.multiselect("Preferred Countries (Max 3)", country_list, max_selections=3)
        
        xls, s_map = load_data()
        course = st.selectbox("Interested Undergrad Course", list(s_map.keys()))
        
        if st.button("Start Assessment"):
            if name and pref_countries:
                st.session_state.update({"name": name, "s_class": s_class, "course": course, "countries": pref_countries, "s_map": s_map, "page": 'questions'})
                st.rerun()
            else: st.warning("Please provide Name and Preferred Countries.")
        st.markdown('</div>', unsafe_allow_html=True)

# PAGE: QUESTIONS
elif st.session_state.page == 'questions':
    xls, _ = load_data()
    df = xls.parse(st.session_state.s_map[st.session_state.course])
    
    st.markdown(f"### Assessment for **{st.session_state.course}**")
    total_score, responses = 0, []

    for idx, row in df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        opts = [f"{c}) {row[f'option_{c}']}" for c in 'ABCDE' if pd.notna(row.get(f'option_{c}'))]
        v_map = {f"{c}) {row[f'option_{c}']}": row[f'score_{c}'] for c in 'ABCDE' if pd.notna(row.get(f'option_{c}'))}
        
        sel = st.selectbox("Select Answer", ["Select..."] + opts, key=f"q{idx}")
        if sel != "Select...":
            total_score += v_map[sel]
            responses.append((row['question_text'], sel, v_map[sel]))
        st.divider()

    if st.button("Calculate My Results"):
        if len(responses) < len(df): st.error("Please answer all questions.")
        else:
            bxls, b_map = load_benchmarking()
            bench = bxls.parse(b_map[st.session_state.course])
            
            # Ideal Score (Avg of Top 3)
            top3 = bench.sort_values("Total Benchmark Score", ascending=False).head(3)
            q_bench = {f"Q{i}": top3[f"Q{i}"].mean() for i in range(1, 11) if f"Q{i}" in bench.columns}
            
            # Country Filter: If 'Country' column exists, filter; otherwise assume USA for provided data.
            if "Country" in bench.columns:
                bench = bench[bench["Country"].isin(st.session_state.countries)]
            
            bench["Score Gap %"] = ((total_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            
            st.session_state.update({"total_score": total_score, "responses": responses, "bench_df": bench, "q_bench": q_bench, "page": 'counsellor'})
            st.rerun()

# PAGE: COUNSELLOR
elif st.session_state.page == 'counsellor':
    st.title("🛡️ Counsellor Authorization")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_name = st.text_input("Counsellor Name *")
        c_code = st.text_input("Authorization Code *", type="password")
        
        if st.button("Generate & Download Report"):
            if c_code == "304" and c_name:
                pdf = generate_pdf(
                    st.session_state.name, st.session_state.s_class, 
                    st.session_state.course, st.session_state.total_score, 
                    st.session_state.responses, st.session_state.bench_df, 
                    st.session_state.q_bench, st.session_state.countries, c_name
                )
                st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_AdmitAI.pdf", mime="application/pdf")
            else: st.error("Invalid authorization code.")
        st.markdown('</div>', unsafe_allow_html=True)
