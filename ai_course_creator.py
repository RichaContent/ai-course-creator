import streamlit as st
import openai
import os
import tempfile
import base64
import fitz  # PyMuPDF
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt

# Use API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# File saving helpers
def save_doc(content, filename):
    doc = Document()
    doc.add_paragraph(content)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    doc.save(filepath)
    return filepath

def save_pptx(slides_text, filename):
    prs = Presentation()
    blank_slide_layout = prs.slide_layouts[1]

    for slide_data in slides_text:
        slide = prs.slides.add_slide(blank_slide_layout)
        title, content = slide.shapes.title, slide.placeholders[1]
        title.text = slide_data["title"]
        content.text = slide_data["content"]

    filepath = os.path.join(tempfile.gettempdir(), filename)
    prs.save(filepath)
    return filepath

# PDF text extraction
def extract_text_from_pdf(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

# Streamlit UI
st.set_page_config(page_title="AI Course Creator", layout="wide")
st.title("📘 AI Course Creator")

st.markdown("Upload SME files (PDF, DOCX, PPTX), and add notes to generate high-quality training content.")

col1, col2 = st.columns(2)

with col1:
    topic = st.text_input("📝 Course Topic", placeholder="e.g. Growth Mindset")
    audience = st.text_input("🎯 Target Audience", placeholder="e.g. First-time managers")
    duration = st.text_input("⏱️ Duration (in minutes)", placeholder="e.g. 90")
    tone = st.selectbox("🎤 Tone of Voice", ["Formal", "Conversational", "Inspiring"])
    level = st.selectbox("📚 Depth of Content", ["Beginner", "Intermediate", "Advanced"])

with col2:
    uploaded_files = st.file_uploader("📂 Upload Reference Files (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
    user_notes = st.text_area("🧠 Add Your Design Notes", placeholder="Include instructional strategy, models to use, specific activities...")

if st.button("🚀 Generate Course"):
    with st.spinner("Generating course content..."):

        # Parse files
        file_texts = []
        for file in uploaded_files:
            ext = file.name.split(".")[-1].lower()
            if ext == "pdf":
                file_texts.append(extract_text_from_pdf(file))
            elif ext == "docx":
                from docx import Document
                doc = Document(file)
                file_texts.append("\n".join([p.text for p in doc.paragraphs]))
            elif ext == "pptx":
                from pptx import Presentation
                prs = Presentation(file)
                slides = []
                for slide in prs.slides:
                    texts = [shape.text for shape in slide.shapes if hasattr(shape, "text")]
                    slides.append("\n".join(texts))
                file_texts.append("\n".join(slides))

        reference_text = "\n\n".join(file_texts)
        system_prompt = f"""You are an expert instructional designer. 
        Generate a detailed course titled "{topic}" for the audience: {audience}. 
        Duration: {duration} minutes. 
        Tone: {tone}. Depth: {level}.

        Reference materials:
        {reference_text}

        Designer's notes:
        {user_notes}

        Output structure:
        1. Course Outline with Timings and Type of Activity (e.g., lecture, role play, case)
        2. Facilitator Guide (step-by-step instructions)
        3. Slide Content (titles and key points)
        4. Quiz (5 MCQs with correct answers)
        5. Workbook Activities (written in 2nd person, with spaces to write, and scenario-based role plays)

        Keep the formatting clean and structured.
        """

        rsp = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": system_prompt}]
        )

        result = rsp.choices[0].message.content

        # Basic parsing
        def extract_section(name):
            try:
                start = result.index(name)
                end = result.index("\n\n", start)
                return result[start:end].strip()
            except:
                return f"{name} not found."

        outline = extract_section("1. Course Outline")
        facilitator = extract_section("2. Facilitator Guide")
        slides_raw = extract_section("3. Slide Content")
        quiz = extract_section("4. Quiz")
        workbook = extract_section("5. Workbook Activities")

        # Convert slides
        slide_blocks = slides_raw.split("\n\n")
        slides = []
        for blk in slide_blocks:
            if ":" in blk:
                title, content = blk.split(":", 1)
                slides.append({"title": title.strip(), "content": content.strip()})

        # Save files
        outline_path = save_doc(outline, "Course_Outline.docx")
        facilitator_path = save_doc(facilitator, "Facilitator_Guide.docx")
        quiz_path = save_doc(quiz, "Quiz.docx")
        workbook_path = save_doc(workbook, "Workbook.docx")
        ppt_path = save_pptx(slides, "Slides.pptx")

        st.success("✅ All files are ready!")

        st.download_button("📥 Download Course Outline", data=open(outline_path, "rb"), file_name="Course_Outline.docx")
        st.download_button("📥 Download Facilitator Guide", data=open(facilitator_path, "rb"), file_name="Facilitator_Guide.docx")
        st.download_button("📥 Download Quiz", data=open(quiz_path, "rb"), file_name="Quiz.docx")
        st.download_button("📥 Download Workbook", data=open(workbook_path, "rb"), file_name="Workbook.docx")
        st.download_button("📥 Download Slide Deck", data=open(ppt_path, "rb"), file_name="Slides.pptx")
