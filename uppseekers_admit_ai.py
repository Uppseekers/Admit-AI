import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Uppseekers Admit AI",
    page_icon="Uppseekers Logo.png",  # <-- Logo is now the page icon
    layout="centered"
)

# ─────────────────────────────────────────────
# LOAD DATA FUNCTIONS
# ─────────────────────────────────────────────
def load_data():
    # This function expects a file named "University Readiness_new.xlsx"
    # in the same directory as the script.
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        index_df = xls.parse(xls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['next_questions_set']))
        return xls, sheet_map
    except FileNotFoundError:
        st.error("Error: The data file 'University Readiness_new.xlsx' was not found.")
        st.stop()


def load_benchmarking():
    # This function expects a file named "Benchmarking_USA.xlsx"
    # in the same directory as the script.
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except FileNotFoundError:
        st.error("Error: The data file 'Benchmarking_USA.xlsx' was not found.")
        st.stop()


# ─────────────────────────────────────────────
# PDF EXPORT FUNCTION
# ─────────────────────────────────────────────
def generate_pdf_with_benchmark(name, student_class, selected_course, total_score, response_summary, benchmark_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Add Logo to PDF
    try:
        logo_path = "Uppseekers Logo.png"
        img = Image(logo_path, width=150, height=45)  # Adjust height as needed
        img.hAlign = 'LEFT'
        elements.append(img)
        elements.append(Spacer(1, 20))
    except FileNotFoundError:
        # Silently pass if logo is not found for PDF generation
        pass

    elements.append(Paragraph(f"Uppseekers Admit AI Report for {name}", styles['Title']))
    elements.append(Paragraph(f"Class: {student_class}", styles['Normal']))
    elements.append(Paragraph(f"Interested Course: {selected_course}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Profile Score: {total_score}", styles['Heading2']))
    elements.append(Spacer(1, 12))

    table_data = [["Question", "Selected Option", "Score"]]
    for q, ans, sc in response_summary:
        table_data.append([q, ans, str(sc)])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(Paragraph("Profile Responses:", styles['Heading3']))
    elements.append(table)
    elements.append(Spacer(1, 18))

    def add_university_section(df, title):
        df = df.sort_values(by="Score Gap %", ascending=False if "Reach" in title else True).head(5)
        if not df.empty:
            elements.append(Paragraph(title, styles['Heading3']))
            uni_table_data = [["University", "Benchmark Score", "Gap %"]]
            for _, row in df.iterrows():
                uni_table_data.append([
                    row["University"],
                    round(row["Total Benchmark Score"], 2),
                    f"{round(row['Score Gap %'], 2)}%"
                ])
            uni_table = Table(uni_table_data, repeatRows=1)
            uni_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(uni_table)
            elements.append(Spacer(1, 12))

    reach = benchmark_df[benchmark_df["Score Gap %"] >= -10]
    maybe = benchmark_df[(benchmark_df["Score Gap %"] < -10) & (benchmark_df["Score Gap %"] >= -25)]
    stretch = benchmark_df[benchmark_df["Score Gap %"] < -25]

    elements.append(Paragraph("University Fit Overview", styles['Heading2']))
    add_university_section(reach, "✅ Within Reach Universities")
    add_university_section(maybe, "🟡 Needs Strengthening")
    add_university_section(stretch, "🔴 Significant Gaps")

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# MULTI-PAGE STATE HANDLING
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    # Use columns to place the icon and title on the same line
    try:
        col1, col2 = st.columns([0.2, 0.8])
        with col1:
            st.image("Uppseekers Logo.png", width=100) # Adjust width for desired size
        with col2:
            st.title("Uppseekers Admit AI")
    except Exception:
        st.error("Logo file not found. Please ensure 'Uppseekers Logo.png' is in the correct folder.")
        st.stop()
        
    name = st.text_input("Student Name")
    student_class = st.selectbox("Student Class", ["9", "10", "11", "12"])
    board = st.selectbox("Board of Education", ["IB", "IGCSE", "CIE", "ICSE", "CBSE", "State Board", "Others"])
    school_name = st.text_input("School Name")
    city = st.selectbox("City", sorted([
        "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
        "Indore", "Bhopal", "Chandigarh", "Nagpur", "Other"
    ]))

    xls, sheet_map = load_data()
    selected_course = st.selectbox("Interested Course for Undergrad", list(sheet_map.keys()))

    if st.button("Next"):
        if name and student_class and selected_course:
            st.session_state.page = 'questions'
            st.session_state.name = name
            st.session_state.student_class = student_class
            st.session_state.selected_course = selected_course
            st.session_state.sheet_map = sheet_map
            st.rerun()
elif st.session_state.page == 'questions':
    name = st.session_state.name
    student_class = st.session_state.student_class
    selected_course = st.session_state.selected_course
    sheet_map = st.session_state.sheet_map

    sheet_name = sheet_map[selected_course]
    xls, _ = load_data()
    questions_df = xls.parse(sheet_name)

    st.markdown(f"### Answer Questions for {selected_course}")
    total_score = 0
    response_summary = []

    for _, row in questions_df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        options = []
        option_map = {}
        for opt in ['A', 'B', 'C', 'D', 'E']:
            opt_text = row.get(f'option_{opt}')
            if pd.notna(opt_text):
                label = f"{opt}) {opt_text.strip()}"
                options.append(label)
                option_map[label] = row.get(f'score_{opt}')
        dropdown_options = ["Select an option..."] + options
        selected = st.selectbox("Select your answer", dropdown_options, key=f"q{row['question_id']}")
        if selected != "Select an option...":
            score = option_map.get(selected, 0)
            total_score += score
        else:
            score = 0
        response_summary.append((row['question_text'], selected, score))

    st.success(f"✅ Total Profile Score: {total_score}")

    if st.button("Next"):
        bxls, bsheet_map = load_benchmarking()
        bsheet = bsheet_map.get(selected_course)
        benchmark_df = pd.DataFrame()
        if bsheet and bsheet in bxls.sheet_names:
            bench_df = bxls.parse(bsheet)
            bench_df["Q1_scaled"] = (bench_df["Q1"] / 20) * 40
            other_qs = [f"Q{i}" for i in range(2, 11) if f"Q{i}" in bench_df.columns]
            bench_df["OtherTotal"] = bench_df[other_qs].sum(axis=1)
            bench_df["Other_scaled"] = (bench_df["OtherTotal"] / 80) * 60
            bench_df["Total Benchmark Score"] = (bench_df["Q1_scaled"] + bench_df["Other_scaled"]).round(2)
            bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
            benchmark_df = bench_df

        st.session_state.total_score = total_score
        st.session_state.response_summary = response_summary
        st.session_state.benchmark_df = benchmark_df
        st.session_state.page = 'parent_info'
        st.rerun()

elif st.session_state.page == 'parent_info':
    st.title("📞 Parent Details & Final Steps")

    download_pref = st.radio("Would you like to download the report?", ["Yes", "No"])
    parent_name = st.text_input("Parent's Name")
    whatsapp = st.text_input("WhatsApp Number (with country code)", placeholder="+919123456789")

    if whatsapp and (not whatsapp.startswith('+') or len(whatsapp) < 11):
        st.warning("Please enter a valid WhatsApp number with country code (e.g., +919123456789)")

    budget = st.selectbox("What is your estimated budget per annum for global universities?", [
        "Less than INR 15 Lacs per annum",
        "15 Lacs to 30 Lacs per annum",
        "More than 30 Lacs per annum"
    ])

    if parent_name and whatsapp.startswith('+') and len(whatsapp) >= 11:
        # Test mode allows immediate download
        if whatsapp == "+000000000000":
            st.success("✅ Test mode: Download your profile report below.")
            pdf_data = generate_pdf_with_benchmark(
                st.session_state.name,
                st.session_state.student_class,
                st.session_state.selected_course,
                st.session_state.total_score,
                st.session_state.response_summary,
                st.session_state.benchmark_df
            )
            st.download_button(
                label="Download Uppseekers Admit AI Report",
                data=pdf_data,
                file_name=f"{st.session_state.name}_Uppseekers_Admit_AI_Report.pdf",
                mime="application/pdf"
            )
        else:
            st.success("✅ Thank you! Our counsellor will call you shortly with the detailed profile report.")
