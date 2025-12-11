import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Uppseekers Admit AI",
    page_icon="Uppseekers Logo.png",
    layout="centered",
)

# -----------------------------
# HELPERS & DATA LOADERS
# -----------------------------

def load_data():
    """
    Loads the main university readiness workbook.
    Expects: University Readiness_new.xlsx in the same folder.
    Returns: pd.ExcelFile, sheet_map (course -> sheetname)
    """
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        index_df = xls.parse(xls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['next_questions_set']))
        return xls, sheet_map
    except FileNotFoundError:
        st.error("Error: The data file 'University Readiness_new.xlsx' was not found.")
        st.stop()


def load_benchmarking():
    """
    Loads benchmarking workbook.
    Expects: Benchmarking_USA.xlsx in the same folder.
    Returns: pd.ExcelFile, sheet_map (course -> benchmarking sheetname)
    """
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except FileNotFoundError:
        st.error("Error: The data file 'Benchmarking_USA.xlsx' was not found.")
        st.stop()


# -----------------------------
# PDF EXPORT
# -----------------------------

def clamp(value, minimum=0, maximum=100):
    try:
        v = float(value)
    except Exception:
        return minimum
    if v < minimum:
        return minimum
    if v > maximum:
        return maximum
    return v


def generate_pdf_with_benchmark(name, student_class, selected_course, total_score, response_summary, benchmark_df):
    """
    Builds a nicer PDF with margins, wrapped text, stable table widths, and clamped benchmark scores.
    Also ensures the tables don't overflow by using sensible column widths and page breaks.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.wordWrap = 'CJK'  # better wrapping for long table cells
    title_style = styles['Title']
    h2 = styles['Heading2']
    h3 = styles['Heading3']

    # custom small paragraph style for table cells
    small = ParagraphStyle('small', parent=normal, fontSize=9, leading=11, alignment=TA_LEFT)

    elements = []

    # Logo (if present)
    try:
        logo_path = "Uppseekers Logo.png"
        img = Image(logo_path)
        img.drawHeight = 16 * mm
        img.drawWidth = 55 * mm
        img.hAlign = 'LEFT'
        elements.append(img)
        elements.append(Spacer(1, 6))
    except Exception:
        # If logo missing we do not fail
        pass

    elements.append(Paragraph(f"Uppseekers Admit AI - Detailed Profile Report", title_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Student: <b>{name}</b>", normal))
    elements.append(Paragraph(f"Class: <b>{student_class}</b>", normal))
    elements.append(Paragraph(f"Interested Course: <b>{selected_course}</b>", normal))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph(f"Total Profile Score: <b>{round(float(total_score),2)}</b>", h2))
    elements.append(Spacer(1, 6))

    # Responses table
    elements.append(Paragraph("Profile Responses", h3))

    # Build table rows but keep cell content short/wrapped to avoid overflow
    table_data = [[Paragraph("Question", small), Paragraph("Selected Option", small), Paragraph("Score", small)]]
    for q, ans, sc in response_summary:
        q_para = Paragraph(str(q), small)
        ans_text = str(ans) if ans else "-"
        # Truncate very long option strings for table but keep full text in separate section if desired
        if len(ans_text) > 120:
            ans_text = ans_text[:117] + '...'
        a_para = Paragraph(ans_text, small)
        s_para = Paragraph(str(sc), small)
        table_data.append([q_para, a_para, s_para])

    col_widths = [100 * mm, 60 * mm, 20 * mm]
    resp_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
    resp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3a6ea5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    elements.append(resp_table)
    elements.append(Spacer(1, 10))

    # University fit sections
    def add_university_section(df, title):
        if df.empty:
            return
        elements.append(Paragraph(title, h3))
        uni_rows = [[Paragraph('University', small), Paragraph('Benchmark Score', small), Paragraph('Gap %', small)]]
        # Sort defensively and clamp benchmark scores to [0,100]
        for _, row in df.iterrows():
            uni = Paragraph(str(row.get('University', '')), small)
            bench_raw = row.get('Total Benchmark Score', 0)
            bench = clamp(round(float(bench_raw), 2), 0, 100)
            gap = row.get('Score Gap %', None)
            gap_text = f"{round(gap,2)}%" if pd.notna(gap) else '-'
            uni_rows.append([uni, Paragraph(str(bench), small), Paragraph(gap_text, small)])

        uni_table = Table(uni_rows, colWidths=[90 * mm, 40 * mm, 30 * mm], repeatRows=1)
        uni_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3a6ea5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ]))
        elements.append(uni_table)
        elements.append(Spacer(1, 8))

    # Prepare three buckets
    if benchmark_df is None or benchmark_df.empty:
        elements.append(Paragraph('No benchmarking data available for the selected course.', normal))
    else:
        # Defensive: ensure correct numeric columns
        bench = benchmark_df.copy()
        # Clamp Total Benchmark Score to 0-100 so display never goes above 100
        if 'Total Benchmark Score' in bench.columns:
            bench['Total Benchmark Score'] = bench['Total Benchmark Score'].apply(lambda x: clamp(x, 0, 100))
        else:
            bench['Total Benchmark Score'] = 0

        # If Score Gap % contains inf or NaN, replace
        if 'Score Gap %' in bench.columns:
            bench['Score Gap %'] = bench['Score Gap %'].replace([pd.NA, pd.NaT], 9999).fillna(9999)
        else:
            bench['Score Gap %'] = 9999

        # Define buckets (these ranges can be tuned in the requirement file)
        reach = bench[bench['Score Gap %'] >= -10].sort_values(by='Score Gap %', ascending=False).head(10)
        maybe = bench[(bench['Score Gap %'] < -10) & (bench['Score Gap %'] >= -25)].sort_values(by='Score Gap %', ascending=False).head(10)
        stretch = bench[bench['Score Gap %'] < -25].sort_values(by='Score Gap %', ascending=False).head(10)

        elements.append(Paragraph('University Fit Overview', h2))
        add_university_section(reach, 'Within Reach Universities')
        add_university_section(maybe, 'Needs Strengthening')
        add_university_section(stretch, 'Significant Gaps (Dream Universities)')

    # Footer note
    elements.append(Spacer(1, 6))
    elements.append(Paragraph('Generated by Uppseekers Admit AI', styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# -----------------------------
# APP STATE & UI
# -----------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    # Header with logo and title
    try:
        col1, col2 = st.columns([0.18, 0.82])
        with col1:
            st.image("Uppseekers Logo.png", width=86)
        with col2:
            st.title("Uppseekers Admit AI")
    except Exception:
        st.title("Uppseekers Admit AI")

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
            st.experimental_rerun()

elif st.session_state.page == 'questions':
    name = st.session_state.name
    student_class = st.session_state.student_class
    selected_course = st.session_state.selected_course
    sheet_map = st.session_state.sheet_map

    sheet_name = sheet_map[selected_course]
    xls, _ = load_data()
    questions_df = xls.parse(sheet_name)

    st.markdown(f"### Answer Questions for {selected_course}")
    total_score = 0.0
    response_summary = []

    for _, row in questions_df.iterrows():
        qid = int(row['question_id']) if not pd.isna(row['question_id']) else 0
        st.markdown(f"**Q{qid}. {row['question_text']}**")
        options = []
        option_map = {}
        for opt in ['A', 'B', 'C', 'D', 'E']:
            opt_text = row.get(f'option_{opt}')
            if pd.notna(opt_text):
                label = f"{opt}) {str(opt_text).strip()}"
                options.append(label)
                # ensure score is numeric
                raw_score = row.get(f'score_{opt}', 0)
                try:
                    score_val = float(raw_score)
                except Exception:
                    score_val = 0.0
                option_map[label] = score_val

        dropdown_options = ["Select an option..."] + options
        selected = st.selectbox("Select your answer", dropdown_options, key=f"q{qid}")
        if selected != "Select an option...":
            score = option_map.get(selected, 0.0)
            total_score += float(score)
        else:
            score = 0.0
        response_summary.append((row['question_text'], selected, score))

    # clamp total score to 100 as well (if your scoring system's max is 100). If your scoring system uses a different max,
    # update this clamp or compute max dynamically and document it in the requirement file.
    total_score = round(clamp(total_score, 0, 100), 2)

    st.success(f"✅ Total Profile Score: {total_score}")

    if st.button("Next"):
        bxls, bsheet_map = load_benchmarking()
        bsheet = bsheet_map.get(selected_course)
        benchmark_df = pd.DataFrame()
        if bsheet and bsheet in bxls.sheet_names:
            bench_df = bxls.parse(bsheet)
            # Defensive scaling: if Q1 exists and max assumed is 20 -> scale to 40, else detect max automatically
            if 'Q1' in bench_df.columns:
                try:
                    bench_df['Q1_scaled'] = (bench_df['Q1'] / 20) * 40
                except Exception:
                    bench_df['Q1_scaled'] = bench_df['Q1']
            else:
                bench_df['Q1_scaled'] = 0

            other_qs = [c for c in bench_df.columns if c.startswith('Q') and c != 'Q1']
            if other_qs:
                bench_df['OtherTotal'] = bench_df[other_qs].sum(axis=1)
                # If OtherTotal max assumed is 80 -> scale to 60
                try:
                    bench_df['Other_scaled'] = (bench_df['OtherTotal'] / 80) * 60
                except Exception:
                    bench_df['Other_scaled'] = bench_df['OtherTotal']
            else:
                bench_df['OtherTotal'] = 0
                bench_df['Other_scaled'] = 0

            bench_df['Total Benchmark Score'] = (bench_df['Q1_scaled'] + bench_df['Other_scaled']).round(2)

            # Avoid division by zero when computing % gap
            bench_df['Total Benchmark Score'] = bench_df['Total Benchmark Score'].replace(0, pd.NA)
            bench_df['Score Gap %'] = ((total_score - bench_df['Total Benchmark Score']) / bench_df['Total Benchmark Score']) * 100
            bench_df['Score Gap %'] = bench_df['Score Gap %'].replace([pd.NA, pd.NaT], 9999).fillna(9999)

            benchmark_df = bench_df

        st.session_state.total_score = total_score
        st.session_state.response_summary = response_summary
        st.session_state.benchmark_df = benchmark_df
        st.session_state.page = 'parent_info'
        st.experimental_rerun()

elif st.session_state.page == 'parent_info':
    st.title("Parent Details & Final Steps")

    download_pref = st.radio("Would you like to download the report?", ["Yes", "No"] )
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

# End of file
