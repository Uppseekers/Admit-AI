import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ─────────────────────────────────────────────
# 1. UI/UX ENHANCEMENTS (Custom CSS)
# ─────────────────────────────────────────────
def apply_custom_css():
    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            background-color: #004aad;
            color: white;
            font-weight: bold;
            border: none;
        }
        .stButton>button:hover { background-color: #003580; border: none; }
        .stSelectbox, .stTextInput { border-radius: 10px; }
        h1 { color: #004aad; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADING
# ─────────────────────────────────────────────
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        index_df = xls.parse(xls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['next_questions_set']))
        return xls, sheet_map
    except:
        st.error("Error: Data file 'University Readiness_new.xlsx' not found.")
        st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except:
        st.error("Error: Data file 'Benchmarking_USA.xlsx' not found.")
        st.stop()

# ─────────────────────────────────────────────
# 3. ENHANCED PDF GENERATION
# ─────────────────────────────────────────────
def generate_pdf_with_benchmark(name, student_class, selected_course, total_score, response_summary, benchmark_df, counsellor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], textColor=colors.HexColor("#004aad"), fontSize=24, spaceAfter=20)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading2'], textColor=colors.HexColor("#333333"), fontSize=14, spaceBefore=10)
    
    elements = []

    # Logo
    try:
        img = Image("Uppseekers Logo.png", width=140, height=40)
        img.hAlign = 'LEFT'
        elements.append(img)
    except: pass

    elements.append(Paragraph("Admit AI: University Readiness Report", title_style))
    
    # Student Info Box
    info_data = [
        [f"Student Name: {name}", f"Class: {student_class}"],
        [f"Target Course: {selected_course}", f"Counsellor: {counsellor}"]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0,0), (-1,-1), colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Score Highlight
    elements.append(Paragraph(f"Your Profile Strength Score: {round(total_score, 2)}", header_style))
    elements.append(Spacer(1, 15))

    # University Sections Logic
    def add_styled_section(df, title, color_hex, limit):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('Section', parent=styles['Heading3'], textColor=colors.HexColor(color_hex), fontSize=14, spaceBefore=15)))
            
            u_data = [["University", "Benchmark", "Match/Gap %"]]
            for _, row in df.sort_values(by="Score Gap %", ascending=False).head(limit).iterrows():
                u_data.append([
                    Paragraph(row["University"], styles['Normal']),
                    str(round(row["Total Benchmark Score"], 1)),
                    f"{'+' if row['Score Gap %'] > 0 else ''}{round(row['Score Gap %'], 1)}%"
                ])
            
            u_table = Table(u_data, colWidths=[300, 100, 100])
            u_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color_hex)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(u_table)
            elements.append(Spacer(1, 10))

    # Buckets per your request
    safe = benchmark_df[benchmark_df["Score Gap %"] >= 0]
    target = benchmark_df[(benchmark_df["Score Gap %"] <= -10) & (benchmark_df["Score Gap %"] >= -20)]
    dream = benchmark_df[benchmark_df["Score Gap %"] < -20]

    add_styled_section(safe, "🟢 SAFE UNIVERSITIES (Top 5)", "#28a745", 5)
    add_styled_section(target, "🟡 TARGET UNIVERSITIES (Top 10)", "#ffc107", 10)
    add_styled_section(dream, "🔴 DREAM UNIVERSITIES (Top 5)", "#dc3545", 5)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP FLOW
# ─────────────────────────────────────────────
apply_custom_css()

if 'page' not in st.session_state:
    st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🚀 Uppseekers Admit AI")
    st.markdown("##### *Data-driven insights for your global education journey.*")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        c1, c2 = st.columns(2)
        with c1: student_class = st.selectbox("Current Class", ["9", "10", "11", "12"])
        with c2: city = st.text_input("City")
        
        xls, sheet_map = load_data()
        selected_course = st.selectbox("Interested Undergrad Course", list(sheet_map.keys()))
        
        if st.button("Start My Assessment"):
            if name:
                st.session_state.update({"name": name, "student_class": student_class, "selected_course": selected_course, "sheet_map": sheet_map, "page": 'questions'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'questions':
    xls, _ = load_data()
    course = st.session_state.selected_course
    questions_df = xls.parse(st.session_state.sheet_map[course])

    st.markdown(f"### 📋 Analyzing Profile for **{course}**")
    
    total_score = 0
    response_summary = []

    for idx, row in questions_df.iterrows():
        with st.container():
            st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
            opts = []
            val_map = {}
            for char in 'ABCDE':
                opt_text = row.get(f'option_{char}')
                if pd.notna(opt_text):
                    label = f"{char}) {str(opt_text).strip()}"
                    opts.append(label)
                    val_map[label] = row.get(f'score_{char}', 0)
            
            selected = st.selectbox("Choose the most accurate option", ["Select..."] + opts, key=f"q{idx}")
            if selected != "Select...":
                score = val_map[selected]
                total_score += score
                response_summary.append((row['question_text'], selected, score))
            st.divider()

    if st.button("Generate My Results"):
        if len(response_summary) < len(questions_df):
            st.warning("Please complete all questions to see your final score.")
        else:
            bxls, bsheet_map = load_benchmarking()
            bsheet = bsheet_map.get(course)
            bench_df = bxls.parse(bsheet)
            bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
            
            st.session_state.update({"total_score": total_score, "response_summary": response_summary, "benchmark_df": bench_df, "page": 'auth'})
            st.rerun()

elif st.session_state.page == 'auth':
    st.title("🛡️ Counsellor Verification")
    st.info("Assessment complete. A counsellor must verify this session to unlock the PDF report.")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_name = st.text_input("Counsellor Name *")
        c_code = st.text_input("Authorization Code *", type="password")
        
        if st.button("Unlock & Download Report"):
            if c_code == "304" and c_name:
                pdf = generate_pdf_with_benchmark(
                    st.session_state.name, st.session_state.student_class, 
                    st.session_state.selected_course, st.session_state.total_score, 
                    st.session_state.response_summary, st.session_state.benchmark_df, c_name
                )
                st.success("Report Generated Successfully!")
                st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_AdmitAI.pdf", mime="application/pdf")
            else:
                st.error("Invalid authorization code.")
        st.markdown('</div>', unsafe_allow_html=True)import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ─────────────────────────────────────────────
# 1. UI/UX ENHANCEMENTS (Custom CSS)
# ─────────────────────────────────────────────
def apply_custom_css():
    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            background-color: #004aad;
            color: white;
            font-weight: bold;
            border: none;
        }
        .stButton>button:hover { background-color: #003580; border: none; }
        .stSelectbox, .stTextInput { border-radius: 10px; }
        h1 { color: #004aad; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADING
# ─────────────────────────────────────────────
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        index_df = xls.parse(xls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['next_questions_set']))
        return xls, sheet_map
    except:
        st.error("Error: Data file 'University Readiness_new.xlsx' not found.")
        st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except:
        st.error("Error: Data file 'Benchmarking_USA.xlsx' not found.")
        st.stop()

# ─────────────────────────────────────────────
# 3. ENHANCED PDF GENERATION
# ─────────────────────────────────────────────
def generate_pdf_with_benchmark(name, student_class, selected_course, total_score, response_summary, benchmark_df, counsellor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], textColor=colors.HexColor("#004aad"), fontSize=24, spaceAfter=20)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading2'], textColor=colors.HexColor("#333333"), fontSize=14, spaceBefore=10)
    
    elements = []

    # Logo
    try:
        img = Image("Uppseekers Logo.png", width=140, height=40)
        img.hAlign = 'LEFT'
        elements.append(img)
    except: pass

    elements.append(Paragraph("Admit AI: University Readiness Report", title_style))
    
    # Student Info Box
    info_data = [
        [f"Student Name: {name}", f"Class: {student_class}"],
        [f"Target Course: {selected_course}", f"Counsellor: {counsellor}"]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0,0), (-1,-1), colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Score Highlight
    elements.append(Paragraph(f"Your Profile Strength Score: {round(total_score, 2)}", header_style))
    elements.append(Spacer(1, 15))

    # University Sections Logic
    def add_styled_section(df, title, color_hex, limit):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('Section', parent=styles['Heading3'], textColor=colors.HexColor(color_hex), fontSize=14, spaceBefore=15)))
            
            u_data = [["University", "Benchmark", "Match/Gap %"]]
            for _, row in df.sort_values(by="Score Gap %", ascending=False).head(limit).iterrows():
                u_data.append([
                    Paragraph(row["University"], styles['Normal']),
                    str(round(row["Total Benchmark Score"], 1)),
                    f"{'+' if row['Score Gap %'] > 0 else ''}{round(row['Score Gap %'], 1)}%"
                ])
            
            u_table = Table(u_data, colWidths=[300, 100, 100])
            u_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color_hex)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(u_table)
            elements.append(Spacer(1, 10))

    # Buckets per your request
    safe = benchmark_df[benchmark_df["Score Gap %"] >= 0]
    target = benchmark_df[(benchmark_df["Score Gap %"] <= -10) & (benchmark_df["Score Gap %"] >= -20)]
    dream = benchmark_df[benchmark_df["Score Gap %"] < -20]

    add_styled_section(safe, "🟢 SAFE UNIVERSITIES (Top 5)", "#28a745", 5)
    add_styled_section(target, "🟡 TARGET UNIVERSITIES (Top 10)", "#ffc107", 10)
    add_styled_section(dream, "🔴 DREAM UNIVERSITIES (Top 5)", "#dc3545", 5)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP FLOW
# ─────────────────────────────────────────────
apply_custom_css()

if 'page' not in st.session_state:
    st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🚀 Uppseekers Admit AI")
    st.markdown("##### *Data-driven insights for your global education journey.*")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        c1, c2 = st.columns(2)
        with c1: student_class = st.selectbox("Current Class", ["9", "10", "11", "12"])
        with c2: city = st.text_input("City")
        
        xls, sheet_map = load_data()
        selected_course = st.selectbox("Interested Undergrad Course", list(sheet_map.keys()))
        
        if st.button("Start My Assessment"):
            if name:
                st.session_state.update({"name": name, "student_class": student_class, "selected_course": selected_course, "sheet_map": sheet_map, "page": 'questions'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'questions':
    xls, _ = load_data()
    course = st.session_state.selected_course
    questions_df = xls.parse(st.session_state.sheet_map[course])

    st.markdown(f"### 📋 Analyzing Profile for **{course}**")
    
    total_score = 0
    response_summary = []

    for idx, row in questions_df.iterrows():
        with st.container():
            st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
            opts = []
            val_map = {}
            for char in 'ABCDE':
                opt_text = row.get(f'option_{char}')
                if pd.notna(opt_text):
                    label = f"{char}) {str(opt_text).strip()}"
                    opts.append(label)
                    val_map[label] = row.get(f'score_{char}', 0)
            
            selected = st.selectbox("Choose the most accurate option", ["Select..."] + opts, key=f"q{idx}")
            if selected != "Select...":
                score = val_map[selected]
                total_score += score
                response_summary.append((row['question_text'], selected, score))
            st.divider()

    if st.button("Generate My Results"):
        if len(response_summary) < len(questions_df):
            st.warning("Please complete all questions to see your final score.")
        else:
            bxls, bsheet_map = load_benchmarking()
            bsheet = bsheet_map.get(course)
            bench_df = bxls.parse(bsheet)
            bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
            
            st.session_state.update({"total_score": total_score, "response_summary": response_summary, "benchmark_df": bench_df, "page": 'auth'})
            st.rerun()

elif st.session_state.page == 'auth':
    st.title("🛡️ Counsellor Verification")
    st.info("Assessment complete. A counsellor must verify this session to unlock the PDF report.")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_name = st.text_input("Counsellor Name *")
        c_code = st.text_input("Authorization Code *", type="password")
        
        if st.button("Unlock & Download Report"):
            if c_code == "304" and c_name:
                pdf = generate_pdf_with_benchmark(
                    st.session_state.name, st.session_state.student_class, 
                    st.session_state.selected_course, st.session_state.total_score, 
                    st.session_state.response_summary, st.session_state.benchmark_df, c_name
                )
                st.success("Report Generated Successfully!")
                st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_AdmitAI.pdf", mime="application/pdf")
            else:
                st.error("Invalid authorization code.")
        st.markdown('</div>', unsafe_allow_html=True)
