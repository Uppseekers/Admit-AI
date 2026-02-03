import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="centered")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #004aad; color: white; font-weight: bold; border: none; }
        .card { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eee; margin-bottom: 20px; }
        .stMultiSelect div { border-radius: 8px; }
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
        st.error("Error: University Readiness_new.xlsx not found.")
        st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, dict(zip(idx.iloc[:,0], idx.iloc[:,1]))
    except:
        st.error("Error: Benchmarking_USA.xlsx not found.")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATION ENGINE (9-LIST LOGIC)
# ─────────────────────────────────────────────
def generate_pdf(name, s_class, course, score, responses, bench_df, q_bench, countries, counsellor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Header
    try:
        elements.append(Image("Uppseekers Logo.png", width=140, height=42))
        elements.append(Spacer(1, 15))
    except: pass

    elements.append(Paragraph(f"Admit AI Analysis: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Class:</b> {s_class} | <b>Course:</b> {course} | <b>Counsellor:</b> {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Overall Profile Score: {round(score, 1)}", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # Improvement Table
    elements.append(Paragraph("1. Improvement Scope Analysis", styles['Heading3']))
    q_data = [["Question", "Score", "Ideal", "Scope"]]
    for i, (q_text, ans, s) in enumerate(responses):
        ideal = q_bench.get(f"Q{i+1}", 0)
        gap = round(ideal - s, 1)
        scope = f"+{gap} pts" if gap > 0 else "Benchmark Met ✅"
        q_data.append([Paragraph(q_text, styles['Normal']), str(s), str(round(ideal, 1)), Paragraph(scope, styles['Normal'])])
    
    qt = Table(q_data, colWidths=[210, 40, 40, 160])
    qt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004aad")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elements.append(qt)
    elements.append(Spacer(1, 25))

    # 9-LIST CURATION (3 Countries x 3 Categories)
    elements.append(Paragraph("2. Country-wise University Curation", styles['Heading2']))
    
    def add_table(df, title, color):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            u_data = [["University", "Score", "Gap %"]]
            for _, row in df.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
            ut = Table(u_data, colWidths=[300, 70, 80])
            ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
            elements.append(ut)
            elements.append(Spacer(1, 10))

    for country in countries:
        elements.append(Paragraph(f"Region: {country}", styles['Heading3']))
        # Filtering for Country (assuming column exists, else using full set for demo)
        c_df = bench_df[bench_df["Country"] == country] if "Country" in bench_df.columns else bench_df
        
        # Split into 3 Lists per Country
        safe = c_df[c_df["Score Gap %"] >= 0]
        target = c_df[(c_df["Score Gap %"] <= -10) & (c_df["Score Gap %"] >= -20)]
        dream = c_df[c_df["Score Gap %"] < -20]

        add_table(safe, f"Safe - {country}", colors.darkgreen)
        add_table(target, f"Target - {country}", colors.orange)
        add_table(dream, f"Dream - {country}", colors.red)
        elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. STREAMLIT APP
# ─────────────────────────────────────────────
apply_styles()
if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        s_class = st.selectbox("Current Class", ["9", "10", "11", "12"])
        country_list = ["USA", "UK", "Canada", "Australia", "Singapore", "Europe"]
        pref_countries = st.multiselect("Preferred Countries (Max 3)", country_list, max_selections=3)
        xls, s_map = load_data()
        course = st.selectbox("Interested Course", list(s_map.keys()))
        if st.button("Start My Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "s_class": s_class, "course": course, "countries": pref_countries, "s_map": s_map, "page": 'questions'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'questions':
    xls, _ = load_data()
    df = xls.parse(st.session_state.s_map[st.session_state.course])
    total_score, responses = 0, []
    st.markdown(f"### Assessment: {st.session_state.course}")
    for idx, row in df.iterrows():
        st.markdown(f"**{row['question_text']}**")
        opts = ["None / Not Applicable"]
        v_map = {"None / Not Applicable": 0}
        for c in 'ABCDE':
            if pd.notna(row.get(f'option_{c}')):
                label = f"{c}) {str(row[f'option_{c}']).strip()}"
                opts.append(label); v_map[label] = row[f'score_{c}']
        sel = st.selectbox("Select Involvement", opts, key=f"q{idx}")
        total_score += v_map[sel]
        responses.append((row['question_text'], sel, v_map[sel]))
        st.divider()
    if st.button("Finalize Results"):
        bxls, b_map = load_benchmarking()
        bench = bxls.parse(b_map[st.session_state.course])
        top3 = bench.sort_values("Total Benchmark Score", ascending=False).head(3)
        q_bench = {f"Q{i}": top3[f"Q{i}"].mean() for i in range(1, 11) if f"Q{i}" in bench.columns}
        bench["Score Gap %"] = ((total_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
        st.session_state.update({"total_score": total_score, "responses": responses, "bench_df": bench, "q_bench": q_bench, "page": 'counsellor'})
        st.rerun()

elif st.session_state.page == 'counsellor':
    st.title("🛡️ Authorization")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_name = st.text_input("Counsellor Name")
        c_code = st.text_input("Access Pin", type="password")
        if st.button("Generate 9-List Report"):
            if c_code == "304" and c_name:
                pdf = generate_pdf(st.session_state.name, st.session_state.s_class, st.session_state.course, st.session_state.total_score, st.session_state.responses, st.session_state.bench_df, st.session_state.q_bench, st.session_state.countries, c_name)
                st.download_button("📥 Download PDF", data=pdf, file_name=f"{st.session_state.name}_Report.pdf", mime="application/pdf")
            else: st.error("Invalid Pin.")
        st.markdown('</div>', unsafe_allow_html=True)
