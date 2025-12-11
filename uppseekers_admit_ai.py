# Uppseekers Admit AI – Streamlit App (Complete Rewritten Version)

```python
import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import io
from PIL import Image

# ---------------------------------------------------------------
# 1. Helpers
# ---------------------------------------------------------------
def clamp(value, min_v=0, max_v=100):
    try:
        v = float(value)
    except:
        return 0
    return max(min_v, min(max_v, v))


def safe_rerun():
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
            return
        except:
            pass
    if hasattr(st, "rerun"):
        st.rerun()
    raise RuntimeError("No Streamlit rerun method available.")

# ---------------------------------------------------------------
# 2. Session Initialization
# ---------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "intro"
if "responses" not in st.session_state:
    st.session_state.responses = {}

# ---------------------------------------------------------------
# 3. Load Data
# ---------------------------------------------------------------
@st.cache_data
def load_data():
    uni_df = pd.read_excel("University Readiness_new.xlsx")
    bench_df = pd.read_excel("Benchmarking_USA.xlsx")
    return uni_df, bench_df

uni_df, bench_df = load_data()

# ---------------------------------------------------------------
# 4. UI Pages
# ---------------------------------------------------------------
def intro():
    st.title("Uppseekers AdmitAI – Readiness & University Matching Tool")
    st.markdown("""
    This tool evaluates a student's readiness based on key academic and achievement parameters
    and maps them to suitable US universities.
    """)
    if st.button("Begin Assessment"):
        st.session_state.page = "questions"
        safe_rerun()


def questions():
    st.header("Student Assessment Questionnaire")

    questions_list = [
        ("academics", "Academic Performance (0–100)", 0, 100),
        ("scores", "Standardized Test Scores (0–100)", 0, 100),
        ("extracurricular", "Extracurricular Strength (0–100)", 0, 100),
        ("research", "Research / Projects (0–100)", 0, 100),
        ("leadership", "Leadership & Impact (0–100)", 0, 100),
    ]

    for key, label, lo, hi in questions_list:
        st.session_state.responses[key] = clamp(
            st.slider(label, lo, hi, st.session_state.responses.get(key, 50))
        )

    if st.button("Continue"):
        st.session_state.page = "parent"
        safe_rerun()


def parent_info():
    st.header("Parent / Student Information")

    st.session_state.responses["student_name"] = st.text_input("Student Name", st.session_state.responses.get("student_name", ""))
    st.session_state.responses["grade"] = st.text_input("Current Grade", st.session_state.responses.get("grade", ""))

    if st.button("Generate Report"):
        st.session_state.page = "report"
        safe_rerun()

# ---------------------------------------------------------------
# 5. Compute Final Score
# ---------------------------------------------------------------
def compute_score(r):
    weights = {
        "academics": 0.40,
        "scores": 0.20,
        "extracurricular": 0.15,
        "research": 0.15,
        "leadership": 0.10,
    }
    total = 0
    for k, w in weights.items():
        total += w * clamp(r.get(k, 0))
    return clamp(total)

# ---------------------------------------------------------------
# 6. University Recommendation Logic
# ---------------------------------------------------------------
def match_universities(score, uni_df, bench_df):
    df = uni_df.copy()
    df["Benchmark Score"] = df["University"].map(
        bench_df.set_index("University")["Benchmark Score"].to_dict()
    )

    df["Benchmark Score"] = df["Benchmark Score"].apply(clamp)
    df["Score Gap %"] = score - df["Benchmark Score"]

    def bucket(gap):
        if gap >= -10:
            return "Within Reach"
        elif gap >= -25:
            return "Needs Strengthening"
        return "Significant Gaps"

    df["Category"] = df["Score Gap %"].apply(bucket)
    return df

# ---------------------------------------------------------------
# 7. PDF Generation
# ---------------------------------------------------------------
def generate_pdf(student, score, df):
    buffer = io.BytesIO()
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Uppseekers AdmitAI Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Student: {student}", styles["Heading2"]))
    story.append(Paragraph(f"Overall Readiness Score: <b>{score}</b>", styles["Heading3"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>University Recommendations</b>", styles["Heading2"]))
    story.append(Spacer(1, 10))

    table_data = [["University", "Benchmark", "Gap", "Category"]]
    for _, row in df.iterrows():
        table_data.append([
            row["University"],
            row["Benchmark Score"],
            row["Score Gap %"],
            row["Category"],
        ])

    tbl = Table(table_data, colWidths=[160, 80, 70, 120])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, -1), "HeiseiMin-W3"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(tbl)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------------
# 8. Report Page
# ---------------------------------------------------------------
def report_page():
    st.header("Your Readiness & Recommendations")

    r = st.session_state.responses
    score = compute_score(r)
    df = match_universities(score, uni_df, bench_df)

    st.subheader(f"Overall Readiness Score: {score}")
    st.dataframe(df)

    pdf_bytes = generate_pdf(r.get("student_name", "Student"), score, df)

    st.download_button(
        label="Download PDF Report",
        data=pdf_bytes,
        file_name="Uppseekers_AdmitAI_Report.pdf",
        mime="application/pdf"
    )

    if st.button("Start Again"):
        st.session_state.page = "intro"
        st.session_state.responses = {}
        safe_rerun()

# ---------------------------------------------------------------
# 9. Page Router
# ---------------------------------------------------------------
if st.session_state.page == "intro":
    intro()
elif st.session_state.page == "questions":
    questions()
elif st.session_state.page == "parent":
    parent_info()
elif st.session_state.page == "report":
    report_page()
```
