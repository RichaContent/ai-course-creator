import streamlit as st
from openai import OpenAI              # new style client
from docx import Document
from pptx import Presentation
from pptx.util import Pt
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import os

# ───────────────────────── App / Key ─────────────────────────
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🧠 AI Training Course Creator")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("Add OPENAI_API_KEY in Secrets before running.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ───────────────────────── Form ──────────────────────────────
with st.form("course_form"):
    topic    = st.text_input("📚 Course Topic")
    audience = st.text_input("👥 Target Audience")
    duration = st.number_input("⏳ Duration (minutes)", 30, 480, step=15)
    tone     = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"])
    level    = st.selectbox("🎚 Complexity", ["Beginner", "Intermediate", "Advanced"])
    submitted = st.form_submit_button("🚀 Generate Course")

# ───────────────────────── Helpers ───────────────────────────
def save_doc(text, fname):
    doc = Document()
    for block in text.split("\n\n"):
        doc.add_paragraph(block)
    doc.save(fname); return fname

def save_ppt(text, fname):
    prs = Presentation()
    for chunk in text.split("\n\n"):
        lines = [l.strip("• ").strip() for l in chunk.split("\n") if l.strip()]
        if not lines: continue
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = lines[0]
        s.placeholders[1].text = "\n".join(lines[1:])
    prs.save(fname); return fname

def zip_bytes(files: dict):
    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as z:
        for arc, p in files.items(): z.write(p, arcname=arc)
    buf.seek(0); return buf

# ───────────────────────── Generate ──────────────────────────
if submitted:
    if not (topic and audience):
        st.error("Please fill every field."); st.stop()

    prompt = f"""
Design a {duration}-minute course on "{topic}" for {audience}.
Tone: {tone.lower()}, Level: {level.lower()}.

Return **exactly** these 5 sections each under an H3 header:

### Course_Outline
Module title | hh:mm | objective(s) | delivery method | brief description

### Slides
Slide 1 Title
• bullet
• bullet

### Quiz
5 MCQs, 4 options, mark correct.

### Workbook
Second-person exercises, blanks, 1 role-play scenario.

### Facilitator_Guide
Step-by-step timings, questions, tips.
"""

    with st.spinner("Generating…"):
        rsp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )

    text   = rsp.choices[0].message.content
    tokens = rsp.usage.total_tokens
    cost   = round(tokens / 1000 * 0.01, 4)
    st.success(f"✅ Done – {tokens} tokens (~${cost})")

    def section(name):
        tag = f"### {name}"
        return text.split(tag)[1].split("###")[0].strip() if tag in text else ""

    outline = section("Course_Outline")
    slides  = section("Slides")
    quiz    = section("Quiz")
    workbk  = section("Workbook")
    guide   = section("Facilitator_Guide")

    outline_p = save_doc(outline, "Course_Outline.docx")
    slides_p  = save_ppt(slides,  "Slides.pptx")
    quiz_p    = save_doc(quiz,    "Quiz.docx")
    work_p    = save_doc(workbk,  "Workbook.docx")
    guide_p   = save_doc(guide,   "Facilitator_Guide.docx")

    # download buttons
    for label, path in [
        ("Outline", outline_p), ("Slides", slides_p),
        ("Quiz", quiz_p), ("Workbook", work_p),
        ("Facilitator Guide", guide_p)
    ]:
        st.download_button(f"📥 {label}", open(path, "rb"),
                           file_name=os.path.basename(path),
                           mime="application/octet-stream")

    # zip
    zip_buf = zip_bytes({
        "Course_Outline.docx": outline_p,
        "Slides.pptx": slides_p,
        "Quiz.docx": quiz_p,
        "Workbook.docx": work_p,
        "Facilitator_Guide.docx": guide_p,
    })
    st.download_button("📦 ALL files (.zip)", zip_buf,
                       file_name="AI_Course.zip", mime="application/zip")
