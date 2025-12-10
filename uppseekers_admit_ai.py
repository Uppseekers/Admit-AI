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
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontSize=24, textColor=BRAND_COLOR, spaceAfter=20)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, textColor=colors.grey)
    h2_style = ParagraphStyle('H2Custom', parent=styles['Heading2'], fontSize=16, textColor=BRAND_COLOR, borderPadding=5, borderColor=colors.lightgrey, borderWidth=0, backColor=colors.whitesmoke, spaceBefore=20, spaceAfter=10)
    
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
    t_summ.setStyle(TableStyle(
