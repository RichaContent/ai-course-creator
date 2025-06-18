import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Pt
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import os

# ── App & key setup ────────────────────────────────────────────────
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🧠 AI Training Course Creator")

# Load key from Streamlit Cloud secrets
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OPENAI_API_KEY not found in Streamlit Secrets. "
             "Add it in Manage App → Settings → Secrets.")
    st.stop()

openai.api_key = st.secrets["OPENAI_API_KEY"]

# ── Input form (all blank by default) ───────────────────────────────
with st.form("course_form"):
    topic    = st.text_input("📖 Course Topic")
    audience = st.text_input("👥 Target Audience")
    duration = st.number_input("⏱ Duration (minutes)", 30, 480, step=15)
    tone     = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"])
    level    = st.selectbox("🎚 Complexity", ["Beginner", "Intermediate", "Advanced"])
    submitted = st.form_submit_button("🚀 Generate Course")

# ── Utilities ──────────────────────────────────────────────────────
def save_doc(text, fname):
    doc = Document()
    for para in text.split("\n\n"):
        doc.add_paragraph(para)
    doc.save(fname); return fname

def save_ppt(slides_txt, fname):
    prs = Presentation(); layout = prs.slide_layouts[1]
    for slide in slides_txt.split("\n\n"):
        lines = [l.strip("• ").strip() for l in slide.split("\n") if l.strip()]
        if not lines: continue
        s = prs.slides.add_slide(layout)
        s.shapes.title.text = lines[0]
        s.placeholders[1].text = "\n".join(lines[1:])
    prs.save(fname); return fname

def zip_files(d):
    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as z:
        for arc, path in d.items(): z.write(path, arcname=arc)
    buf.seek(0); return buf

# ── Main generation block ──────────────────────────────────────────
if submitted:
    if not all([topic, audience]):
        st.error("Please fill in every field."); st.stop()

    prompt = f"""
Design a {duration}-minute training course on “{topic}” for {audience}.
Tone: {tone.lower()}, Level: {level.lower()}.

Return exactly five sections with these H3 markers:

### Course_Outline
- Module title | hh:mm | objectives | delivery method | brief content

### Slides
Slide 1 Title
• Bullet
• Bullet

### Quiz
Q1 …  
A. …  
B. …  
C. … (Correct)  
D. …

### Workbook
Second-person activities, blanks, 1 role-play scenario.

### Facilitator_Guide
Step-by-step instructions, timings, tips.
"""

    with st.spinner("Generating course…"):
        rsp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
    txt   = rsp.choices[0].message.content
    toks  = rsp.usage.total_tokens
    cost  = round(toks / 1000 * 0.01, 4)
    st.success(f"✅ Done – {toks} tokens (~${cost})")

    # split output
    def grab(tag):
        marker = f"### {tag}"
        return txt.split(marker)[1].split("###")[0].strip() if marker in txt else ""
    outline = grab("Course_Outline")
    slides  = grab("Slides")
    quiz    = grab("Quiz")
    wb      = grab("Workbook")
    guide   = grab("Facilitator_Guide")

    # save files
    out_path   = save_doc(outline, "Course_Outline.docx")
    ppt_path   = save_ppt(slides,  "Slides.pptx")
    quiz_path  = save_doc(quiz,    "Quiz.docx")
    wb_path    = save_doc(wb,      "Workbook.docx")
    guide_path = save_doc(guide,   "Facilitator_Guide.docx")

    # download buttons (force File Save dialog)
    def dl(label, path):
        st.download_button(label, open(path, "rb"), file_name=os.path.basename(path),
                           mime="application/octet-stream")
    col1, col2 = st.columns(2)
    with col1:
        dl("📥 Outline", out_path)
        dl("📥 Slides",  ppt_path)
        dl("📥 Quiz",    quiz_path)
    with col2:
        dl("📥 Workbook", wb_path)
        dl("📥 Facilitator Guide", guide_path)

    # zip all
    all_zip = zip_files({
        "Course_Outline.docx": out_path,
        "Slides.pptx": ppt_path,
        "Quiz.docx": quiz_path,
        "Workbook.docx": wb_path,
        "Facilitator_Guide.docx": guide_path
    })
    st.download_button("📦 Download ALL (.zip)", data=all_zip, file_name="AI_Course.zip", mime="application/zip")
