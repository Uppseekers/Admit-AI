import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ─────────────────────────────────────────────
# CONFIG & ASSETS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Uppseekers Admit AI",
    page_icon="🎯", 
    layout="centered"
)

def load_excel_file(file_name):
    try:
        xls = pd.ExcelFile(file_name)
        index_df = xls.parse(xls.sheet_names[0])
        # Mapping first column to second column for sheet routing
        sheet_map = dict(zip(index_df.iloc[:, 0], index_df.iloc[:, 1]))
        return xls, sheet_map
    except FileNotFoundError:
        st.error(f"Error: '{file_name}' not found.")
        return None, None

# ─────────────────────────────────────────────
# PDF GENERATION ENGINE
# ─────────────────────────────────────────────
def generate_improved_pdf(name, student_class, selected_course, total_score, response_summary, benchmark_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor("#1D3557"), alignment=TA_CENTER, spaceAfter=20)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=12, leading=14)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor("#457B9D"), spaceBefore=15, spaceAfter=10)

    elements = []

    # 1. Header & Branding
    try:
        img = Image("Uppseekers Logo.png", width=140, height=40)
        img.hAlign = 'LEFT'
        elements.append(img)
    except:
        pass
    
    elements.append(Paragraph("University Readiness Analysis", title_style))
    elements.append(Paragraph(f"<b>Student:</b> {name} | <b>Class:</b> {student_class}", sub_style))
    elements.append(Paragraph(f"<b>Target Course:</b> {selected_course}", sub_style))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"Overall Profile Score: {total_score}", heading_style))
    elements.append(Spacer(1, 10))

    # 2. Score Breakdown Table
    elements.append(Paragraph("Detailed Profile Breakdown", styles['Heading3']))
    table_data = [["Category/Question", "Response", "Score"]]
    for q, ans, sc in response_summary:
        # Truncate long questions for PDF fit
        q_short = (q[:60] + '...') if len(q) > 60 else q
        table_data.append([Paragraph(q_short, styles['Normal']), Paragraph(str(ans), styles['Normal']), str(sc)])

    resp_table = Table(table_data, colWidths=[300, 130, 50])
    resp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1D3557")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))
    elements.append(resp_table)
    elements.append(Spacer(1, 20))

    # 3. University Recommendations
    elements.append(Paragraph("University Fit & Suggestions", heading_style))

    def create_uni_table(df, category_name, color_hex):
        if df.empty: return
        elements.append(Paragraph(f"{category_name}", ParagraphStyle('cat', parent=styles['Heading4'], textColor=colors.HexColor(color_hex))))
        
        u_data = [["University", "Bench. Score", "Gap %", "Suggested Action"]]
        for _, row in df.iterrows():
            gap = row["Score Gap %"]
            # Logic for suggestions
            if gap < -25:
                advice = "Focus on significant profile building (Internships/Projects)."
            elif gap < -10:
                advice = "Improve standardized test scores or GPA slightly."
            else:
                advice = "Strong fit. Maintain current academic trajectory."

            u_data.append([row["University"], round(row["Total Benchmark Score"], 1), f"{round(gap, 1)}%", Paragraph(advice, styles['Small'])])

        u_table = Table(u_data, colWidths=[140, 80, 60, 200])
        u_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F4F9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(u_table)
        elements.append(Spacer(1, 10))

    # Splitting logic
    safe = benchmark_df[benchmark_df["Score Gap %"] >= 0].sort_values(by="Score Gap %", ascending=False)
    target = benchmark_df[(benchmark_df["Score Gap %"] < 0) & (benchmark_df["Score Gap %"] >= -15)]
    reach = benchmark_df[benchmark_df["Score Gap %"] < -15].sort_values(by="Score Gap %", ascending=False)

    create_uni_table(safe, "✅ Safe Schools (Strong Admission Chance)", "#2A9D8F")
    create_uni_table(target, "🟡 Should Try / Target Schools (Competitive)", "#E9C46A")
    create_uni_table(reach, "🔴 Reach / Difficult Schools (High Gaps)", "#E76F51")

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# UI FLOW
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

# --- Page: Intro ---
if st.session_state.page == 'intro':
    st.title("🚀 Uppseekers Admit AI")
    st.info("Let's analyze your profile readiness for global universities.")
    
    with st.form("student_details"):
        name = st.text_input("Full Name")
        student_class = st.selectbox("Current Grade", ["9", "10", "11", "12"])
        
        xls, sheet_map = load_excel_file("University Readiness_new.xlsx")
        course_list = list(sheet_map.keys()) if sheet_map else []
        selected_course = st.selectbox("Intended Major", course_list)
        
        submitted = st.form_submit_button("Start Assessment")
        if submitted:
            if name and selected_course:
                st.session_state.update({"name": name, "student_class": student_class, 
                                         "selected_course": selected_course, "sheet_map": sheet_map, "page": 'questions'})
                st.rerun()

# --- Page: Questions ---
elif st.session_state.page == 'questions':
    st.header(f"Profile Questions: {st.session_state.selected_course}")
    xls, _ = load_excel_file("University Readiness_new.xlsx")
    sheet_name = st.session_state.sheet_map[st.session_state.selected_course]
    q_df = xls.parse(sheet_name)

    responses = []
    total_score = 0

    with st.form("questions_form"):
        for _, row in q_df.iterrows():
            st.write(f"**{row['question_text']}**")
            opts = {f"{row[f'option_{c}']}".strip(): row[f'score_{c}'] for c in ['A','B','C','D','E'] if pd.notna(row.get(f'option_{c}'))}
            
            choice = st.radio("Choose one:", list(opts.keys()), key=f"q_{row['question_id']}")
            score = opts.get(choice, 0)
            responses.append((row['question_text'], choice, score))
            total_score += score
        
        if st.form_submit_button("Calculate Results"):
            st.session_state.total_score = total_score
            st.session_state.response_summary = responses
            st.session_state.page = 'results'
            st.rerun()

# --- Page: Results & Benchmarking ---
elif st.session_state.page == 'results':
    st.header("📊 Your Profile Analysis")
    
    # Process Benchmarking
    bxls, b_map = load_excel_file("Benchmarking_USA.xlsx")
    bsheet = b_map.get(st.session_state.selected_course)
    
    if bsheet and bsheet in bxls.sheet_names:
        bench_df = bxls.parse(bsheet)
        # Scaling logic as per your previous code
        bench_df["Q1_scaled"] = (bench_df.iloc[:, 1] / 20) * 40 # Assuming Q1 is column index 1
        other_qs = bench_df.columns[2:11] # Q2 to Q10
        bench_df["Other_scaled"] = (bench_df[other_qs].sum(axis=1) / 80) * 60
        bench_df["Total Benchmark Score"] = (bench_df["Q1_scaled"] + bench_df["Other_scaled"]).round(2)
        bench_df["Score Gap %"] = ((st.session_state.total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
        
        st.success(f"Profile Score: {st.session_state.total_score}")
        
        # Download Section
        st.divider()
        st.subheader("Get Your Detailed PDF Report")
        parent_name = st.text_input("Parent's Name")
        whatsapp = st.text_input("WhatsApp Number (e.g. +91...)")

        if st.button("Generate & Download PDF"):
            if parent_name and whatsapp:
                pdf = generate_improved_pdf(
                    st.session_state.name, st.session_state.student_class,
                    st.session_state.selected_course, st.session_state.total_score,
                    st.session_state.response_summary, bench_df
                )
                st.download_button("Download Now", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
            else:
                st.warning("Please fill in parent details to download.")
    else:
        st.error("Benchmarking data for this course is unavailable.")

    if st.button("Restart"):
        st.session_state.page = 'intro'
        st.rerun()
