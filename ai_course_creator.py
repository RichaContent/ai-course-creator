# AI Course Creator - Final Working Script (Streamlit Cloud Compatible)

import streamlit as st
from openai import OpenAI
import os
import tempfile
import docx2txt
import PyPDF2
from pptx import Presentation
from docx import Document
from io import BytesIO
import zipfile

# Load API Key from Secrets
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Streamlit Page Setup
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# Backup: Allow Manual API Key Entry (Optional)
if not api_key:
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    if not api_key:
        st.warning("API key required.")
        st.stop()
    client = OpenAI(api_key=api_key)

# Inputs
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience (e.g., Mid-Level Managers)")
duration = st.slider("Duration (minutes)", 30, 300, 90, 30)
tone = st.selectbox("Tone", ["Professional", "Conversational", "Inspirational", "Academic"])

st.header("Step 2: (Optional) Upload References")
uploaded_files = st.file_uploader("Upload PDFs, Word, or PPTX", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
user_notes = st.text_area("Optional Notes")
feedback = st.text_area("Any Feedback (Optional)")

# Extract Text
extracted_text = ""
for file in uploaded_files:
    if file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            extracted_text += page.extract_text() or ""
    elif file.name.endswith(".docx"):
        extracted_text += docx2txt.process(file)
    elif file.name.endswith(".pptx"):
        ppt = Presentation(file)
        for slide in ppt.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    extracted_text += shape.text + "\n"

# Prompt Engineering
prompt = f"""
Create a {duration}-minute training course on: "{topic}" for this audience: {audience}.
Use a {tone.lower()} tone.

Return:
1. Course_Outline: In tabular format (Time | Activity Type | Description).
2. Facilitator_Guide: Rich with explanations, examples, case studies, transitions.
3. Participant_Workbook: With instructions, exercises, reflection questions.
4. Quiz: With MCQs, MMCQs, True/False. Include an answer key.
5. Slide_Deck: One slide per section with bullet points (text only).

{f"Refer to notes: {user_notes}" if user_notes else ""}
{f"Revise based on feedback: {feedback}" if feedback else ""}
{f"Use this reference material: {extracted_text}" if extracted_text else ""}
"""

if st.button("Generate Course Materials"):
    with st.spinner("Generating with GPT-4o..."):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.choices[0].message.content

            # Split into sections
            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Participant_Workbook": "", "Quiz": "", "Slide_Deck": ""}
            current = None
            for line in result.splitlines():
                line_stripped = line.strip()
                for key in sections:
                    if key.lower().replace("_", " ") in line_stripped.lower():
                        current = key
                        break
                else:
                    if current:
                        sections[current] += line + "\n"

            def save_docx(text, filename):
                doc = Document()
                for line in text.strip().splitlines():
                    doc.add_paragraph(line)
                path = os.path.join(tempfile.gettempdir(), filename)
                doc.save(path)
                return path

            paths = {
                "Course_Outline.docx": save_docx(sections["Course_Outline"], "Course_Outline.docx"),
                "Facilitator_Guide.docx": save_docx(sections["Facilitator_Guide"], "Facilitator_Guide.docx"),
                "Participant_Workbook.docx": save_docx(sections["Participant_Workbook"], "Participant_Workbook.docx"),
                "Quiz.docx": save_docx(sections["Quiz"], "Quiz.docx"),
                "Slide_Deck.docx": save_docx(sections["Slide_Deck"], "Slide_Deck.docx"),
            }

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for filename, path in paths.items():
                    zipf.write(path, arcname=filename)
            zip_buffer.seek(0)

            st.success("✅ Course materials generated successfully.")
            st.download_button("📦 Download All as ZIP", zip_buffer, file_name="Course_Materials.zip")

            for filename, path in paths.items():
                with open(path, "rb") as f:
                    st.download_button(f"📥 {filename}", f, file_name=filename)

            st.caption(f"Tokens used: {response.usage.total_tokens} (approx. ${(response.usage.total_tokens/1000)*0.01:.4f})")

        except Exception as e:
            st.error(f"❌ Error generating content: {e}")
