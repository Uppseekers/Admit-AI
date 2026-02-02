import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. APP CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Uppseekers Admit AI",
    page_icon="Uppseekers Logo.png",
    layout="centered"
)

# ─────────────────────────────────────────────
# 2. DATA LOADING FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        # Assuming first sheet contains the mapping of course to question set
        index_df = xls.parse(xls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['next_questions_set']))
        return xls, sheet_map
    except Exception as e:
        st.error(f"Error loading 'University Readiness_new.xlsx': {e}")
        st.stop()

@st.cache_data
def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        # Assuming first sheet contains the mapping of course to benchmarking set
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except Exception as e:
        st.error(f"Error loading 'Benchmarking_USA.xlsx': {e}")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATION FUNCTION
# ─────────────────────────────────────────────
def generate_pdf_report(name, student_class, selected_course, total_score, response_summary, benchmark_df, counsellor_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles for wrapping text in tables
    style_normal = styles["Normal"]
    style_heading = styles["Heading2"]
    
    elements = []

    # Add Logo
    try:
        logo = Image("Uppseekers Logo.png", width=120, height=40)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 15))
    except:
        pass

    # Header Details
    elements.append(Paragraph(f"Admit AI Analysis Report", styles['Title']))
    elements.append(Paragraph(f"<b>Student Name:</b> {name}", style_normal))
    elements.append(Paragraph(f"<b>Class:</b> {student_class}", style_normal))
    elements.append(Paragraph(f"<b>Target Course:</b> {selected_course}", style_normal))
    elements.append(Paragraph(f"<b>Assisting Counsellor:</b> {counsellor_name}", style_normal))
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph(f"Total Profile Score: {round(total_score, 2)}", style_heading))
    elements.append(Spacer(1, 12))

    # Profile Response Table
    table_data = [["Question", "Selected Option", "Score"]]
    for q, ans, sc in response_summary:
        # Wrap text using Paragraph for better fit
        table_data.append([
            Paragraph(q, style_normal),
            Paragraph(ans, style_normal),
            str(sc)
        ])
    
    res_table = Table(table_data, colWidths=[240, 180, 50], repeatRows=1)
    res_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))
    elements.append(Paragraph("Detailed Profile Responses", styles['Heading3']))
    elements.append(res_table)
    elements.append(Spacer(1, 20))

    # University Fit Tables
    def create_fit_section(df, title, header_color):
        if not df.empty:
            elements.append(Paragraph(title, styles['Heading3']))
            u_data = [["University", "Benchmark", "Gap %"]]
            for _, row in df.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                u_data.append([
                    row["University"], 
                    str(round(row["Total Benchmark Score"], 1)), 
                    f"{round(row['Score Gap %'], 1)}%"
                ])
            u_table = Table(u_data, colWidths=[280, 100, 90])
            u_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(u_table)
            elements.append(Spacer(1, 15))

    reach = benchmark_df[benchmark_df["Score Gap %"] >= -10]
    maybe = benchmark_df[(benchmark_df["Score Gap %"] < -10) & (benchmark_df["Score Gap %"] >= -25)]
    stretch = benchmark_df[benchmark_df["Score Gap %"] < -25]

    create_fit_section(reach, "✅ Within Reach Universities", colors.darkgreen)
    create_fit_section(maybe, "🟡 Target / Needs Strengthening", colors.orange)
    create_fit_section(stretch, "🔴 Significant Gap Universities", colors.crimson)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. MULTI-PAGE NAVIGATION
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

# --- PAGE 1: INTRO ---
if st.session_state.page == 'intro':
    try:
        st.image("Uppseekers Logo.png", width=180)
    except:
        pass
    st.title("Uppseekers Admit AI")
    st.write("Welcome! Let's assess your profile readiness for global universities.")
    
    name = st.text_input("Student Name")
    student_class = st.selectbox("Student Class", ["9", "10", "11", "12"])
    school_name = st.text_input("School Name")
    city = st.text_input("City")
    
    xls, sheet_map = load_data()
    selected_course = st.selectbox("Interested Course for Undergrad", list(sheet_map.keys()))

    if st.button("Start Assessment"):
        if name and school_name and city:
            st.session_state.update({
                "name": name,
                "student_class": student_class,
                "selected_course": selected_course,
                "sheet_map": sheet_map,
                "page": 'questions'
            })
            st.rerun()
        else:
            st.warning("Please fill in all the details to proceed.")

# --- PAGE 2: QUESTIONS ---
elif st.session_state.page == 'questions':
    xls, _ = load_data()
    course = st.session_state.selected_course
    sheet_name = st.session_state.sheet_map[course]
    questions_df = xls.parse(sheet_name)

    st.subheader(f"Profiling: {course}")
    total_score = 0
    response_summary = []

    # Display Questions
    for idx, row in questions_df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        
        # Build options dynamically
        opts = []
        val_map = {}
        for char in 'ABCDE':
            opt_text = row.get(f'option_{char}')
            if pd.notna(opt_text):
                label = f"{char}) {str(opt_text).strip()}"
                opts.append(label)
                val_map[label] = row.get(f'score_{char}', 0)
        
        choice = st.selectbox("Your Answer", ["Select an option..."] + opts, key=f"q_{idx}")
        
        if choice != "Select an option...":
            sc = val_map[choice]
            total_score += sc
            response_summary.append((row['question_text'], choice, sc))

    if st.button("Complete Assessment"):
        if len(response_summary) < len(questions_df):
            st.error("Please answer all questions before submitting.")
        else:
            # Load and Process Benchmarks
            bxls, bsheet_map = load_benchmarking()
            bsheet = bsheet_map.get(course)
            
            if bsheet and bsheet in bxls.sheet_names:
                bench_df = bxls.parse(bsheet)
                # Benchmark logic fix: Use raw scores from the sheet (e.g. 95.9, etc)
                # Ensure we are comparing raw sum to raw sum
                bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
                
                st.session_state.update({
                    "total_score": total_score,
                    "response_summary": response_summary,
                    "benchmark_df": bench_df,
                    "page": 'parent_info'
                })
                st.rerun()
            else:
                st.error("Benchmarking data for this course is missing.")

# --- PAGE 3: PARENT & COUNSELLOR SECURITY ---
elif st.session_state.page == 'parent_info':
    st.title("Finalize Your Report")
    
    st.subheader("Parent Details")
    parent_name = st.text_input("Parent's Name")
    whatsapp = st.text_input("WhatsApp Number (+91...)")
    budget = st.selectbox("Estimated Annual Budget", ["< 15 Lacs", "15-30 Lacs", "> 30 Lacs"])
    
    st.divider()
    st.subheader("Counsellor Authorization")
    st.info("The section below is for office use only.")
    counsellor_name = st.text_input("Counsellor Name")
    access_code = st.text_input("Access Code", type="password")

    if st.button("Generate Admit AI Report"):
        if not (parent_name and whatsapp and counsellor_name):
            st.error("All fields (Parent and Counsellor) are required.")
        elif access_code != "#304":
            st.error("Invalid Access Code. Please contact the administrator.")
        else:
            # Code is correct, generate PDF
            st.success("Authorization Successful!")
            pdf_data = generate_pdf_report(
                st.session_state.name,
                st.session_state.student_class,
                st.session_state.selected_course,
                st.session_state.total_score,
                st.session_state.response_summary,
                st.session_state.benchmark_df,
                counsellor_name
            )
            
            st.download_button(
                label="📥 Download Detailed Report (PDF)",
                data=pdf_data,
                file_name=f"{st.session_state.name}_Uppseekers_Report.pdf",
                mime="application/pdf"
            )
