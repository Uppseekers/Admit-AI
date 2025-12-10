import streamlit as st
import pandas as pd
import io
# Removed matplotlib and numpy imports to prevent ModuleNotFoundError
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Line # Import ReportLab graphics
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Uppseekers Admit AI",
    page_icon="🎓", 
    layout="centered"
)

# Brand Colors
BRAND_COLOR = colors.Color(0.1, 0.2, 0.5) # Navy Blue
ACCENT_COLOR = colors.Color(1, 0.6, 0.2)  # Gold/Orange
LIGHT_GREY = colors.Color(0.95, 0.95, 0.95)

# ─────────────────────────────────────────────
# MOCK DATA GENERATORS (FALLBACK)
# ─────────────────────────────────────────────
def get_mock_questions():
    """Generates dummy data if Excel is missing so you can see the PDF design"""
    data = {
        'question_id': [1, 2, 3, 4],
        'question_text': [
            "What is your current GPA range?",
            "How many extracurricular activities do you lead?",
            "Have you taken SAT/ACT?",
            "Rate your essay writing skills."
        ],
        'option_A': ["< 3.0", "None", "No", "Basic"],
        'option_B': ["3.0 - 3.5", "1-2", "Planned", "Average"],
        'option_C': ["3.5 - 3.8", "3-4", "Yes, low score", "Good"],
        'option_D': ["3.8 - 4.0", "5+", "Yes, high score", "Excellent"],
        'option_E': [None, None, None, None],
        'score_A': [5, 5, 0, 5],
        'score_B': [10, 10, 5, 10],
        'score_C': [15, 15, 10, 15],
        'score_D': [20, 20, 20, 20],
        'score_E': [0, 0, 0, 0]
    }
    return pd.DataFrame(data)

def get_mock_benchmarks():
    """Generates dummy university data"""
    data = {
        'University': ['Harvard', 'Stanford', 'MIT', 'UCLA', 'NYU', 'Boston U', 'Purdue'],
        'Q1': [20, 19, 20, 18, 16, 14, 12], # Raw scores to be scaled
        'Q2': [10, 10, 10, 8, 8, 6, 6],
        'Q3': [10, 10, 10, 8, 8, 6, 6]
    }
    # Create enough columns to mimic real sheet
    df = pd.DataFrame(data)
    for i in range(4, 11):
        df[f'Q{i}'] = 8
    return df

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
        # RETURN MOCK DATA FOR DEMO
        # st.warning("⚠️ Excel file not found. Using Mock Data.")
        mock_map = {"Computer Science": "Sheet1", "Economics": "Sheet1"}
        return None, mock_map

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        index_df = bxls.parse(bxls.sheet_names[0])
        sheet_map = dict(zip(index_df['course'], index_df['benchmarking_set']))
        return bxls, sheet_map
    except FileNotFoundError:
        mock_map = {"Computer Science": "Sheet1", "Economics": "Sheet1"}
        return None, mock_map

# ─────────────────────────────────────────────
# ADVANCED PDF GENERATION
# ─────────────────────────────────────────────
def create_header_footer(canvas, doc):
    """Draws the persistent header and footer on every page"""
    canvas.saveState()
    
    # --- HEADER ---
    # Draw a colored band at the top
    canvas.setFillColor(BRAND_COLOR)
    canvas.rect(0, A4[1] - 50, A4[0], 50, fill=True, stroke=False)
    
    # Text in Header
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(30, A4[1] - 32, "Uppseekers Admit AI")
    
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(A4[0] - 30, A4[1] - 32, f"Report Generated: {datetime.now().strftime('%Y-%m-%d')}")

    # --- FOOTER ---
    canvas.setStrokeColor(colors.lightgrey)
    canvas.line(30, 50, A4[0]-30, 50)
    
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(30, 35, "Confidential Advisory Report")
    canvas.drawRightString(A4[0] - 30, 35, f"Page {doc.page}")
    
    canvas.restoreState()

def generate_gap_chart(df, student_score):
    """
    Creates a Vector Graphic chart using ReportLab primitives
    Does NOT require matplotlib or numpy
    """
    # Prepare Data
    df = df.head(7).copy()
    universities = df['University'].tolist()
    uni_scores = df['Total Benchmark Score'].tolist()
    
    # Drawing Configuration
    width = 450
    height = 200
    d = Drawing(width, height)
    
    bar_height = 15
    spacing = 25
    max_possible_score = 100
    chart_width = 300
    scale = chart_width / max_possible_score
    
    start_x = 100
    start_y = height - 30
    
    # Chart Title (Manual Label)
    # d.add(String(width/2, height-10, "Gap Analysis", textAnchor='middle', fontName="Helvetica-Bold"))

    for i, (uni, score) in enumerate(zip(universities, uni_scores)):
        y_pos = start_y - (i * spacing)
        
        # 1. University Label
        d.add(String(5, y_pos + 4, uni, fontName="Helvetica", fontSize=10, textAnchor='start'))
        
        # 2. Determine Color based on Gap
        gap = student_score - score
        if gap >= -10:
            bar_color = colors.HexColor('#2ecc71') # Green
        elif gap >= -25:
            bar_color = colors.HexColor('#f1c40f') # Yellow
        else:
            bar_color = colors.HexColor('#e74c3c') # Red
            
        # 3. Draw Bar
        bar_len = score * scale
        d.add(Rect(start_x, y_pos, bar_len, bar_height, fillColor=bar_color, strokeColor=None))
        
        # 4. Score Label
        d.add(String(start_x + bar_len + 5, y_pos + 4, f"{int(score)}", fontName="Helvetica", fontSize=8, fillColor=colors.grey))

    # 5. Student Score Line
    student_x = start_x + (student_score * scale)
    line_top = start_y + 10
    line_bottom = start_y - (len(universities) * spacing) + 10
    
    d.add(Line(student_x, line_top, student_x, line_bottom, strokeColor=colors.Color(0.1, 0.2, 0.5), strokeWidth=2, strokeDashArray=[2,2]))
    d.add(String(student_x, line_top + 5, "You", fontName="Helvetica-Bold", fontSize=8, textAnchor='middle', fillColor=colors.Color(0.1, 0.2, 0.5)))
    
    return d

def generate_pdf_pro(name, student_class, selected_course, total_score, response_summary, benchmark_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=70, bottomMargin=70)
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'MainTitle', 
        parent=styles['Heading1'], 
        fontSize=24, 
        textColor=BRAND_COLOR, 
        spaceAfter=20
    )
    subtitle_style = ParagraphStyle(
        'SubTitle', 
        parent=styles['Normal'], 
        fontSize=12, 
        textColor=colors.grey
    )
    h2_style = ParagraphStyle(
        'H2Custom', 
        parent=styles['Heading2'], 
        fontSize=16, 
        textColor=BRAND_COLOR, 
        borderPadding=5, 
        borderColor=colors.lightgrey, 
        borderWidth=0, 
        backColor=colors.whitesmoke, 
        spaceBefore=20, 
        spaceAfter=10
    )
    
    elements = []

    # 1. EXECUTIVE SUMMARY BOX
    elements.append(Paragraph(f"Admissions Readiness Report", title_style))
    
    summary_data = [
        [Paragraph("<b>Student Name:</b>", styles['Normal']), name],
        [Paragraph("<b>Class:</b>", styles['Normal']), student_class],
        [Paragraph("<b>Target Major:</b>", styles['Normal']), selected_course],
        [Paragraph("<b>Readiness Score:</b>", styles['Normal']), f"{total_score} / 100"]
    ]
    
    t_summ = Table(summary_data, colWidths=[2*inch, 4*inch])
    
    # Define style list explicitly to avoid syntax errors with nested brackets
    summ_style_cmds = [
        ('BACKGROUND', (0,0), (-1,-1), colors.aliceblue),
        ('TEXTCOLOR', (0,0), (0,-1), BRAND_COLOR),
        ('GRID', (0,0), (-1,-1), 1, colors.white),
        ('PADDING', (0,0), (-1,-1), 10),
    ]
    t_summ.setStyle(TableStyle(summ_style_cmds))
    
    elements.append(t_summ)
    elements.append(Spacer(1, 25))

    # 2. VISUAL GAP ANALYSIS (CHART)
    if not benchmark_df.empty:
        elements.append(Paragraph("University Fit Visualization", h2_style))
        elements.append(Paragraph("This chart compares your current profile score against the benchmark requirements for your target universities.", styles['Normal']))
        elements.append(Spacer(1, 10))
        
        # Generate chart (now returns a Drawing object, not an image buffer)
        chart_drawing = generate_gap_chart(benchmark_df, total_score)
        elements.append(chart_drawing)
        elements.append(Spacer(1, 20))

    # 3. DETAILED UNIVERSITY TABLE
    elements.append(Paragraph("Detailed University Breakdown", h2_style))
    
    if not benchmark_df.empty:
        table_data = [["University", "Required Score", "Your Gap", "Status"]]
        
        sorted_df = benchmark_df.sort_values(by="Score Gap %", ascending=False).head(10)
        
        for _, row in sorted_df.iterrows():
            gap = row['Score Gap %']
            status = "✅ Reachable" if gap >= -10 else ("🟡 Moderate" if gap >= -25 else "🔴 High Reach")
            status_color = colors.green if gap >= -10 else (colors.orange if gap >= -25 else colors.red)
            
            # For PDF styling of text color
            row_data = [
                row["University"],
                f"{row['Total Benchmark Score']:.1f}",
                f"{gap:.1f}%",
                Paragraph(f"<font color={status_color}>{status}</font>", styles['Normal'])
            ]
            table_data.append(row_data)

        uni_table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        
        uni_style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Align Uni names left
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]
        uni_table.setStyle(TableStyle(uni_style_cmds))
        
        elements.append(uni_table)
        elements.append(PageBreak())

    # 4. PROFILE RESPONSES (Page 2)
    elements.append(Paragraph("Profile Assessment Details", h2_style))
    
    resp_data = [["Question", "Your Answer", "Pts"]]
    for q, ans, sc in response_summary:
        # Wrap long text
        resp_data.append([Paragraph(q, styles['Normal']), Paragraph(ans, styles['Normal']), str(sc)])
        
    resp_table = Table(resp_data, colWidths=[3.5*inch, 2.5*inch, 1*inch])
    
    resp_style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ]
    resp_table.setStyle(TableStyle(resp_style_cmds))
    
    elements.append(resp_table)

    # BUILD PDF
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# APP LOGIC
# ─────────────────────────────────────────────

# Initialize Session State
if 'page' not in st.session_state:
    st.session_state.page = 'intro'

# --- PAGE 1: INTRO ---
if st.session_state.page == 'intro':
    col1, col2 = st.columns([0.2, 0.8])
    with col1:
        # Check if logo exists, else use emoji
        try:
            st.image("Uppseekers Logo.png", width=100)
        except:
            st.write("🎓")
    with col2:
        st.title("Uppseekers Admit AI")
        st.caption("AI-Powered University Readiness Assessment")

    with st.container(border=True):
        name = st.text_input("Student Name")
        col_a, col_b = st.columns(2)
        with col_a:
            student_class = st.selectbox("Student Class", ["9", "10", "11", "12"])
            school_name = st.text_input("School Name")
        with col_b:
            board = st.selectbox("Board", ["IB", "IGCSE", "CBSE", "ICSE", "State", "Others"])
            city = st.text_input("City")

        xls, sheet_map = load_data()
        selected_course = st.selectbox("Intended Major", list(sheet_map.keys()))

    if st.button("Start Assessment", type="primary"):
        if name and selected_course:
            st.session_state.page = 'questions'
            st.session_state.name = name
            st.session_state.student_class = student_class
            st.session_state.selected_course = selected_course
            st.session_state.sheet_map = sheet_map
            st.session_state.xls_obj = xls # Pass the file object or None
            st.rerun()
        else:
            st.warning("Please enter Name and Course to proceed.")

# --- PAGE 2: QUESTIONS ---
elif st.session_state.page == 'questions':
    name = st.session_state.name
    selected_course = st.session_state.selected_course
    xls = st.session_state.xls_obj
    sheet_map = st.session_state.sheet_map

    st.markdown(f"### 📝 Assessment: {selected_course}")
    st.progress(0.5, text="Answering Profile Questions")

    # Load Data (Real or Mock)
    if xls:
        sheet_name = sheet_map[selected_course]
        questions_df = xls.parse(sheet_name)
    else:
        questions_df = get_mock_questions() # Fallback

    total_score = 0
    response_summary = []

    with st.form("quiz_form"):
        for _, row in questions_df.iterrows():
            st.markdown(f"**{row['question_text']}**")
            
            # Construct options dynamically
            options = []
            option_scores = {}
            for opt in ['A', 'B', 'C', 'D', 'E']:
                opt_val = row.get(f'option_{opt}')
                if pd.notna(opt_val):
                    options.append(opt_val)
                    option_scores[opt_val] = row.get(f'score_{opt}', 0)
            
            selected = st.radio(f"Select answer for Q{row['question_id']}", options, index=None, key=f"q_{row['question_id']}")
            
            if selected:
                score = option_scores.get(selected, 0)
                total_score += score
                response_summary.append((row['question_text'], selected, score))
            else:
                response_summary.append((row['question_text'], "Not Answered", 0))

        submitted = st.form_submit_button("Calculate Score & Benchmarks")
        
        if submitted:
            st.session_state.total_score = total_score
            st.session_state.response_summary = response_summary
            
            # --- BENCHMARKING LOGIC ---
            bxls, bsheet_map = load_benchmarking()
            
            if bxls:
                # Real Data Logic
                bsheet = bsheet_map.get(selected_course)
                if bsheet:
                    bench_df = bxls.parse(bsheet)
                    # Normalize scores (assuming similar logic to your original code)
                    bench_df["Q1_scaled"] = (bench_df["Q1"] / 20) * 40
                    # Sum other columns dynamically
                    other_cols = [c for c in bench_df.columns if c.startswith('Q') and c != 'Q1']
                    bench_df["OtherTotal"] = bench_df[other_cols].sum(axis=1)
                    bench_df["Other_scaled"] = (bench_df["OtherTotal"] / 80) * 60 # Approx scaling
                    bench_df["Total Benchmark Score"] = (bench_df["Q1_scaled"] + bench_df["Other_scaled"]).round(2)
                    bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
                    st.session_state.benchmark_df = bench_df
            else:
                # Mock Data Logic
                bench_df = get_mock_benchmarks()
                bench_df["Total Benchmark Score"] = bench_df["Q1"] + bench_df["Q2"] + bench_df["Q3"] + 15 # Fake math
                bench_df["Score Gap %"] = ((total_score - bench_df["Total Benchmark Score"]) / bench_df["Total Benchmark Score"]) * 100
                st.session_state.benchmark_df = bench_df
            
            st.session_state.page = 'results'
            st.rerun()

# --- PAGE 3: RESULTS & DOWNLOAD ---
elif st.session_state.page == 'results':
    st.title("📊 Analysis Complete")
    
    score = st.session_state.total_score
    
    # Display Score visually
    col1, col2, col3 = st.columns(3)
    with col2:
        st.metric(label="Your Readiness Score", value=f"{score}/100")
    
    st.divider()
    
    st.write("### 📥 Get Your Official Report")
    
    col_a, col_b = st.columns(2)
    with col_a:
        parent_name = st.text_input("Parent's Name")
    with col_b:
        whatsapp = st.text_input("WhatsApp Number (+91...)")

    if st.button("Generate Professional PDF"):
        if parent_name and whatsapp:
            # Generate the fancy PDF
            pdf_data = generate_pdf_pro(
                st.session_state.name,
                st.session_state.student_class,
                st.session_state.selected_course,
                st.session_state.total_score,
                st.session_state.response_summary,
                st.session_state.benchmark_df
            )
            
            st.success("Report Generated Successfully!")
            st.download_button(
                label="📄 Download Uppseekers Report",
                data=pdf_data,
                file_name=f"{st.session_state.name}_Uppseekers_Report.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Please provide parent details to unlock the download.")
            
    st.divider()
    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()
