# ai_course_creator_app.py

import streamlit as st
import openai
import os
import tempfile
from pptx import Presentation
from pptx.util import Inches, Pt
from docx import Document
from io import BytesIO
import zipfile
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Streamlit page config
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# API Key
api_key = os.getenv("OPENAI_API_KEY") or st.text_input("Enter your OpenAI API Key", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()
openai.api_key = api_key

# Step 1: Course Inputs
st.header("Step 1: Course Information")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience")
duration = st.slider("Course Duration (minutes)", 30, 300, 90, 15)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# Step 2: Optional Inputs
st.header("Step 2 (Optional): Upload Reference Files and Notes")
user_files = st.file_uploader("Upload Files (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
user_notes = st.text_area("Your Notes or Custom Instructions")
feedback = st.text_area("Prior Feedback to Consider")

# Helper: Extract content from files
def extract_text_from_files(files):
    full_text = ""
    for file in files:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            for page in reader.pages:
                full_text += page.extract_text() or ""
        elif file.name.endswith(".docx"):
            doc = Document(file)
            for para in doc.paragraphs:
                full_text += para.text + "\n"
        elif file.name.endswith(".pptx"):
            ppt = Presentation(file)
            for slide in ppt.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        full_text += shape.text + "\n"
    return full_text.strip()

# Helper: Save Word file
def save_word(text, filename):
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(path)
    return path

# Helper: Save slide deck

def save_pptx(slides_text, filename):
    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    bullet_slide_layout = prs.slide_layouts[1]
    lines = slides_text.strip().split("\n")
    current_title, bullets = None, []

    def add_slide(title, bullet_lines):
        slide = prs.slides.add_slide(bullet_slide_layout)
        slide.shapes.title.text = title
        content = slide.placeholders[1].text = "\n".join(bullet_lines)

    for line in lines:
        if line.strip() == "":
            continue
        if not line.startswith("-") and not current_title:
            current_title = line.strip()
        elif line.startswith("-"):
            bullets.append(line.lstrip("- ").strip())
        elif current_title:
            add_slide(current_title, bullets)
            current_title, bullets = line.strip(), []

    if current_title:
        add_slide(current_title, bullets)

    path = os.path.join(tempfile.gettempdir(), filename)
    prs.save(path)
    return path

# Generate Button
if st.button("Generate Course Materials"):
    with st.spinner("Generating using GPT-4o..."):
        try:
            file_text = extract_text_from_files(user_files) if user_files else ""
            prompt = f"""
            Design a {duration}-minute training course on "{topic}" for "{audience}" with a {tonality.lower()} tone.
            Include:
            1. Course Outline in a table format with time, activity type, and description.
            2. Facilitator Guide with case study explanations, discussion tips, transitions.
            3. Participant Workbook with exercises, instructions, and activities.
            4. Quiz with MCQs, MMCQs, and True/False + answer key.
            5. A PowerPoint slide deck (1 slide per idea with bullets, quotes, key points).
            {f"Incorporate the following notes: {user_notes}" if user_notes else ""}
            {f"Consider this feedback: {feedback}" if feedback else ""}
            {f"Reference this material: {file_text}" if file_text else ""}
            Format each section as: ===Section Name=== before the content.
            """
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            reply = response.choices[0].message.content

            # Parse Sections
            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Workbook": "", "Quiz": "", "Slide_Deck": ""}
            current = None
            for line in reply.splitlines():
                if line.startswith("==="):
                    section = line.strip("= ").replace(" ", "_")
                    if section in sections:
                        current = section
                elif current:
                    sections[current] += line + "\n"

            paths = {}
            paths["Course_Outline"] = save_word(sections["Course_Outline"], "Course_Outline.docx")
            paths["Facilitator_Guide"] = save_word(sections["Facilitator_Guide"], "Facilitator_Guide.docx")
            paths["Workbook"] = save_word(sections["Workbook"], "Participant_Workbook.docx")
            paths["Quiz"] = save_word(sections["Quiz"], "Quiz.docx")
            paths["Slide_Deck"] = save_pptx(sections["Slide_Deck"], "Slide_Deck.pptx")

            # ZIP all
            zip_io = BytesIO()
            with zipfile.ZipFile(zip_io, "w") as zf:
                for name, path in paths.items():
                    zf.write(path, os.path.basename(path))
            zip_io.seek(0)

            st.success("✅ Course Materials Ready")
            st.download_button("📦 Download All as ZIP", zip_io, file_name="Course_Materials.zip")

            for name, path in paths.items():
                st.download_button(f"⬇️ Download {name.replace('_', ' ')}", open(path, "rb"), file_name=os.path.basename(path))

        except Exception as e:
            st.error(f"Error generating content: {e}")
