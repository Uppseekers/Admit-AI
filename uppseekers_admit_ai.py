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

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except FileNotFoundError:
        st.error("Error: Data file 'Benchmarking_USA.xlsx' not found.")
        st.stop()

# ─────────────────────────────────────────────
# PDF EXPORT FUNCTION
# ─────────────────────────────────────────────
def generate_pdf_with_benchmark(name, student_class, selected_course, total_score, response_summary, benchmark_df, question_benchmarks):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Title'], alignment=1, textColor=colors.HexColor("#004aad")))
    styles.add(ParagraphStyle(name='SafeStyle', parent=styles['Normal'], textColor=colors.darkgreen))
    styles.add(ParagraphStyle(name='DreamStyle', parent=styles['Normal'], textColor=colors.red))

    elements = []

    try:
        elements.append(Image("Uppseekers Logo.png", width=150, height=45))
        elements.append(Spacer(1, 20))
    except: pass

    elements.append(Paragraph(f"Admit AI Readiness Report: {name}", styles['CenterTitle']))
    elements.append(Paragraph(f"Class: {student_class} | Interested Course: {selected_course}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"Total Profile Score: {round(total_score, 2)}", styles['Heading2']))
    elements.append(Spacer(1, 10))

    # --- SECTION: QUESTION-WISE GAP ANALYSIS ---
    elements.append(Paragraph("1. Detailed Question-wise Gap Analysis", styles['Heading3']))
    table_data = [["Question", "Your Score", "Ideal Score", "Improvement Scope"]]
    
    for i, (q_text, selected, score) in enumerate(response_summary):
        ideal = question_benchmarks.get(f"Q{i+1}", 0)
        gap = round(ideal - score, 2)
        scope_text = f"+{gap} points needed" if gap > 0 else "Benchmark Met ✅"
        
        table_data.append([
            Paragraph(q_text, styles['Normal']),
            str(score),
            str(round(ideal, 1)),
            Paragraph(scope_text, styles['SafeStyle'] if gap <= 0 else styles['DreamStyle'])
        ])

    q_table = Table(table_data, colWidths=[200, 70, 70, 120], repeatRows=1)
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(q_table)
    elements.append(Spacer(1, 25))

    # --- SECTION: UNIVERSITY FIT ---
    elements.append(Paragraph("2. University Admission Probability", styles['Heading3']))
    
    def add_uni_table(df, title, limit, color):
        df = df.sort_values(by="Score Gap %", ascending=False).head(limit)
        if not df.empty:
            elements.append(Paragraph(title, styles['Heading3']))
            u_data = [["University", "Target Score", "Gap %"]]
            for _, row in df.iterrows():
                u_data.append([row["University"], round(row["Total Benchmark Score"], 1), f"{round(row['Score Gap %'], 1)}%"])
            
            u_table = Table(u_data, colWidths=[280, 100, 100])
            u_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            elements.append(u_table)
            elements.append(Spacer(1, 15))

    safe = benchmark_df[benchmark_df["Score Gap %"] >= 0]
    target = benchmark_df[(benchmark_df["Score Gap %"] <= -10) & (benchmark_df["Score Gap %"] >= -20)]
    dream = benchmark_df[benchmark_df["Score Gap %"] < -20]

    add_uni_table(safe, "🟢 Safe Universities", 5, colors.darkgreen)
    add_uni_table(target, "🟡 Target Universities", 10, colors.orange)
    add_uni_table(dream, "🔴 Dream Universities", 5, colors.red)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# APP FLOW
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🚀 Uppseekers Admit AI")
    name = st.text_input("Student Name")
    student_class = st.selectbox("Student Class", ["9", "10", "11", "12"])
    
    # NEW: Preferred Countries Selection
    # Based on common international destinations. Adjust list as needed.
    country_options = ["USA", "UK", "Canada", "Australia", "Germany", "Singapore", "Netherlands", "France"]
    preferred_countries = st.multiselect("Preferred Countries (Max 3)", country_options, max_selections=3)
    
    xls, sheet_map = load_data()
    selected_course = st.selectbox("Interested Course", list(sheet_map.keys()))

    if st.button("Next"):
        if name and preferred_countries:
            st.session_state.update({
                "name": name, 
                "student_class": student_class, 
                "selected_course": selected_course, 
                "preferred_countries": preferred_countries,
                "sheet_map": sheet_map, 
                "page": 'questions'
            })
            st.rerun()
        else:
            st.warning("Please enter your name and select at least one preferred country.")

elif st.session_state.page == 'questions':
    xls, _ = load_data()
    course = st.session_state.selected_course
    questions_df = xls.parse(st.session_state.sheet_map[course])

    st.markdown(f"### Assessment for {course}")
    total_score = 0
    response_summary = []

    for _, row in questions_df.iterrows():
        st.markdown(f"**{row['question_text']}**")
        opts = [f"{c}) {row[f'option_{c}']}" for c in 'ABCDE' if pd.notna(row.get(f'option_{c}'))]
        val_map = {f"{c}) {row[f'option_{c}']}" : row[f'score_{c}'] for c in 'ABCDE' if pd.notna(row.get(f'option_{c}'))}
        
        selected = st.selectbox("Select Answer", ["Select..."] + opts, key=f"q{row['question_id']}")
        if selected != "Select...":
            sc = val_map[selected]
            total_score += sc
            response_summary.append((row['question_text'], selected, sc))
        st.divider()

    if st.button("Submit & Calculate"):
        bxls, bsheet_map = load_benchmarking()
        bench_df = bxls.parse(bsheet_map[course])
        
        # FILTER: Only show universities in preferred countries if your Excel has a 'Country' column
        # If your Excel doesn't have a 'Country' column yet, this part will be skipped.
        if "Country" in bench_df.columns:
            bench_df = bench_df[bench_df["Country"].isin(st.session_state.preferred_countries)]
        
        # Ideal Profile Calculation
        top_unis = bench_df.sort_values(by="Total Benchmark Score", ascending=False).head(3)
        question_benchmarks = {f"Q{i}": top_unis[f"Q{i}"].mean() for i in range(1, 11) if f"Q{i}" in bench_df.columns}
        
        bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
        
        st.session_state.update({
            "total_score": total_score,
            "response_summary": response_summary,
            "benchmark_df": bench_df,
            "question_benchmarks": question_benchmarks,
            "page": 'counsellor_info'
        })
        st.rerun()

elif st.session_state.page == 'counsellor_info':
    st.title("🔒 Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Code", type="password")

    if st.button("Unlock Report"):
        if c_code == "304" and c_name:
            pdf = generate_pdf_with_benchmark(
                st.session_state.name, st.session_state.student_class, 
                st.session_state.selected_course, st.session_state.total_score, 
                st.session_state.response_summary, st.session_state.benchmark_df,
                st.session_state.question_benchmarks
            )
            st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_Admit_AI.pdf", mime="application/pdf")
