import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Uppseekers Admit AI",
    page_icon="Uppseekers Logo.png",
    layout="centered"
)

# ─────────────────────────────────────────────
# LOAD DATA FUNCTIONS
# ─────────────────────────────────────────────
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        index_df = xls.parse(xls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['next_questions_set']))
        return xls, sheet_map
    except FileNotFoundError:
        st.error("Error: Data file 'University Readiness_new.xlsx' not found.")
        st.stop()

def load_benchmarking(country):
    # Dynamically look for the file based on country selection
    # Defaulting to USA if others are not found for this demo
    filename = f"Benchmarking_{country}.xlsx"
    try:
        bxls = pd.ExcelFile(filename)
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except FileNotFoundError:
        if country != "USA":
            st.warning(f"Data for {country} not found. Defaulting to USA benchmarking.")
            return load_benchmarking("USA")
        st.error("Benchmarking data file not found.")
        st.stop()

# ─────────────────────────────────────────────
# PDF EXPORT FUNCTION
# ─────────────────────────────────────────────
def generate_pdf_with_benchmark(name, student_class, selected_course, preferred_country, total_score, response_summary, benchmark_df, question_benchmarks):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Title'], alignment=1, textColor=colors.HexColor("#004aad")))
    styles.add(ParagraphStyle(name='SafeText', parent=styles['Normal'], textColor=colors.darkgreen))
    styles.add(ParagraphStyle(name='TargetText', parent=styles['Normal'], textColor=colors.orange))
    styles.add(ParagraphStyle(name='DreamText', parent=styles['Normal'], textColor=colors.red))

    elements = []

    # Logo
    try:
        elements.append(Image("Uppseekers Logo.png", width=150, height=45))
        elements.append(Spacer(1, 15))
    except: pass

    elements.append(Paragraph(f"Admit AI Readiness Report", styles['CenterTitle']))
    elements.append(Spacer(1, 10))
    
    # Header Info Table
    header_data = [
        [f"Student: {name}", f"Class: {student_class}"],
        [f"Target Course: {selected_course}", f"Preferred Country: {preferred_country}"]
    ]
    h_table = Table(header_data, colWidths=[230, 230])
    h_table.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'), ('TEXTCOLOR', (0,0), (-1,-1), colors.grey)]))
    elements.append(h_table)
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Overall Profile Score: {round(total_score, 2)}", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # --- SECTION 1: QUESTION-WISE IMPROVEMENT ---
    elements.append(Paragraph("1. Skills & Profile Improvement Scope", styles['Heading3']))
    elements.append(Paragraph("Comparison against top-tier global university standards (Ideal Profile).", styles['Italic']))
    
    q_table_data = [["Question", "Score", "Ideal", "Improvement Scope"]]
    for i, (q_text, selected, score) in enumerate(response_summary):
        ideal = question_benchmarks.get(f"Q{i+1}", 0)
        gap = round(ideal - score, 2)
        scope = f"+{gap} pts needed" if gap > 0 else "Benchmark Met ✅"
        
        q_table_data.append([
            Paragraph(q_text, styles['Normal']),
            str(score),
            str(round(ideal, 1)),
            Paragraph(scope, styles['SafeText'] if gap <= 0 else styles['DreamText'])
        ])

    q_table = Table(q_table_data, colWidths=[210, 50, 50, 130], repeatRows=1)
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#004aad")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
    ]))
    elements.append(q_table)
    elements.append(Spacer(1, 25))

    # --- SECTION 2: UNIVERSITY CURATION ---
    elements.append(Paragraph(f"2. Curated Universities in {preferred_country}", styles['Heading3']))
    
    def add_bucket(df, title, limit, header_color):
        df = df.sort_values(by="Score Gap %", ascending=False).head(limit)
        if not df.empty:
            elements.append(Paragraph(title, styles['Heading3']))
            u_data = [["University", "Target Score", "Gap %"]]
            for _, row in df.iterrows():
                u_data.append([row["University"], round(row["Total Benchmark Score"], 1), f"{round(row['Score Gap %'], 1)}%"])
            
            u_table = Table(u_data, colWidths=[290, 100, 100])
            u_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            elements.append(u_table)
            elements.append(Spacer(1, 15))

    # Filtering logic as per request
    safe = benchmark_df[benchmark_df["Score Gap %"] >= 0]
    target = benchmark_df[(benchmark_df["Score Gap %"] <= -10) & (benchmark_df["Score Gap %"] >= -20)]
    dream = benchmark_df[benchmark_df["Score Gap %"] < -20]

    add_bucket(safe, "🟢 SAFE UNIVERSITIES (Top 5 Matches)", 5, colors.darkgreen)
    add_bucket(target, "🟡 TARGET UNIVERSITIES (Top 10 Matches)", 10, colors.orange)
    add_bucket(dream, "🔴 DREAM UNIVERSITIES (Top 5 Matches)", 5, colors.red)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# STREAMLIT PAGES
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

# --- PAGE 1: INTRODUCTION ---
if st.session_state.page == 'intro':
    st.title("🚀 Uppseekers Admit AI")
    st.write("Analyze your profile readiness for top global universities.")
    
    name = st.text_input("Student Name *")
    
    col1, col2 = st.columns(2)
    with col1:
        student_class = st.selectbox("Current Class", ["9", "10", "11", "12"])
        city = st.text_input("City")
    with col2:
        # NEW: Preferred Country Dropdown
        preferred_country = st.selectbox("Preferred Country", [
            "USA", "UK", "Canada", "Australia", "Germany", "Ireland", "Singapore", "Netherlands", "Other"
        ])
        board = st.selectbox("Education Board", ["IB", "IGCSE", "CBSE", "ICSE", "State Board", "Other"])

    xls, sheet_map = load_data()
    selected_course = st.selectbox("Interested Course", list(sheet_map.keys()))

    if st.button("Start Assessment"):
        if name and city:
            st.session_state.update({
                "name": name, "student_class": student_class, "city": city,
                "preferred_country": preferred_country, "selected_course": selected_course,
                "sheet_map": sheet_map, "page": 'questions'
            })
            st.rerun()
        else:
            st.error("Please fill in the required fields.")

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'questions':
    xls, _ = load_data()
    course = st.session_state.selected_course
    questions_df = xls.parse(st.session_state.sheet_map[course])

    st.subheader(f"Profiling Assessment: {course}")
    total_score = 0
    responses = []

    for idx, row in questions_df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        opts = [f"{c}) {row[f'option_{c}']}" for c in 'ABCDE' if pd.notna(row.get(f'option_{c}'))]
        val_map = {f"{c}) {row[f'option_{c}']}" : row[f'score_{c}'] for c in 'ABCDE' if pd.notna(row.get(f'option_{c}'))}
        
        choice = st.selectbox("Select Answer", ["Select..."] + opts, key=f"q_{idx}")
        if choice != "Select...":
            sc = val_map[choice]
            total_score += sc
            responses.append((row['question_text'], choice, sc))
        st.divider()

    if st.button("Submit & See Fit"):
        if len(responses) < len(questions_df):
            st.warning("Please answer all questions.")
        else:
            # Load Benchmarks for the specific country
            bxls, bsheet_map = load_benchmarking(st.session_state.preferred_country)
            bench_df = bxls.parse(bsheet_map[course])
            
            # Question-wise Improvement Scope (Top 3 Average)
            top_3 = bench_df.sort_values("Total Benchmark Score", ascending=False).head(3)
            q_benchmarks = {f"Q{i}": top_3[f"Q{i}"].mean() for i in range(1, 11) if f"Q{i}" in bench_df.columns}
            
            # Gap % for universities
            bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
            
            st.session_state.update({
                "total_score": total_score, "response_summary": responses,
                "benchmark_df": bench_df, "question_benchmarks": q_benchmarks,
                "page": 'auth'
            })
            st.rerun()

# --- PAGE 3: COUNSELLOR AUTHORIZATION ---
elif st.session_state.page == 'auth':
    st.title("🛡️ Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Code", type="password")

    if st.button("Generate & Download Report"):
        if c_code == "304" and c_name:
            st.success("Authorization Successful.")
            pdf = generate_pdf_with_benchmark(
                st.session_state.name, st.session_state.student_class, 
                st.session_state.selected_course, st.session_state.preferred_country,
                st.session_state.total_score, st.session_state.response_summary, 
                st.session_state.benchmark_df, st.session_state.question_benchmarks
            )
            st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_AdmitAI.pdf", mime="application/pdf")
        else:
            st.error("Invalid Code.")
