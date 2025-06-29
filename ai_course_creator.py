    import streamlit as st
import os
import tempfile
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches, Pt
from io import BytesIO
import zipfile
from dotenv import load_dotenv
import PyPDF2
import docx2txt
from typing import Dict

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# App Title
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# Input: API Key fallback
if not os.getenv("OPENAI_API_KEY"):
    api_key = st.text_input("Enter your OpenAI API Key", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()
    client = OpenAI(api_key=api_key)

# Step 1: Course Details
st.header("Step 1: Course Details")
topic = st.text_input("📌 Course Topic")
audience = st.text_input("🎯 Target Audience (e.g., Mid-Level Managers)")
duration = st.slider("⏱️ Duration (in minutes)", 30, 300, 90, step=15)
tonality = st.selectbox("🎤 Tone of Voice", ["Professional", "Conversational", "Inspiring", "Academic"])

# Step 2: Upload reference files
st.header("Step 2 (Optional): Upload Reference Files and Notes")
uploaded_files = st.file_uploader("📂 Upload Reference Files (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
notes = st.text_area("📝 Add Notes or Specific Requirements (Optional)")

# Step 3: Feedback for revision
st.header("Step 3 (Optional): Feedback for Revision")
feedback = st.text_area("💡 Any feedback or changes for AI to consider? (Optional)")

# Extract content from uploaded files
def extract_uploaded_content(files) -> str:
    text = ""
    for file in files:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text += docx2txt.process(file) + "\n"
        elif file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            ppt = Presentation(file)
            for slide in ppt.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
    return text

# Generate Course Button
if st.button("🚀 Generate Course Materials"):
    with st.spinner("Generating your complete course... please wait."):

        extracted_text = extract_uploaded_content(uploaded_files)

        prompt = f"""
You are an expert instructional designer. Create a {duration}-minute training course on "{topic}" for "{audience}" in a {tonality.lower()} tone.

Use any provided notes or file content to improve relevance.

Requirements:
1️⃣ Course Outline:
- Provide a table with columns: Time, Activity Type, Description (max 1 line per row).

2️⃣ Facilitator Guide:
- Detailed instructions, session objectives, key messages, transitions.
- Include definitions, case studies, and examples to support delivery.

3️⃣ Participant Workbook:
- Reflection prompts, spaces for notes, role-play scenarios.

4️⃣ Quiz:
- 5-8 questions, mix of MCQ, MMCQ, True/False with an Answer Key.

5️⃣ Slide Deck:
- Create a 7-10 slide outline with slide titles and 2-4 bullets each for a .pptx deck.

{"Additional notes: " + notes if notes else ""}
{"Reference content: " + extracted_text[:2000] if extracted_text else ""}

Return each section clearly marked as:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
"""

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-preview",
                messages=[{"role": "system", "content": "You are a helpful AI assistant."},
                          {"role": "user", "content": prompt}]
            )
            response = completion.choices[0].message.content

            # Parse sections
            sections = {"COURSE_OUTLINE": "", "FACILITATOR_GUIDE": "", "PARTICIPANT_WORKBOOK": "", "QUIZ": "", "SLIDE_DECK": ""}
            current_section = None
            for line in response.splitlines():
                stripped = line.strip()
                if stripped in [f"## {key}" for key in sections.keys()]:
                    current_section = stripped.replace("## ", "")
                elif current_section:
                    sections[current_section] += line + "\n"

            # Save DOCX files
            def save_docx(content, filename):
                from docx import Document
                doc = Document()
                for line in content.strip().splitlines():
                    doc.add_paragraph(line)
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                doc.save(temp_path)
                return temp_path

            outline_path = save_docx(sections["COURSE_OUTLINE"], "Course_Outline.docx")
            guide_path = save_docx(sections["FACILITATOR_GUIDE"], "Facilitator_Guide.docx")
            workbook_path = save_docx(sections["PARTICIPANT_WORKBOOK"], "Participant_Workbook.docx")
            quiz_path = save_docx(sections["QUIZ"], "Quiz.docx")

            # Generate PPTX slide deck
            prs = Presentation()
            for slide_text in sections["SLIDE_DECK"].strip().split("\n\n"):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                lines = slide_text.strip().split("\n")
                if lines:
                    slide.shapes.title.text = lines[0]
                    for point in lines[1:]:
                        slide.placeholders[1].text += f"{point}\n"
            slide_path = os.path.join(tempfile.gettempdir(), "Slide_Deck.pptx")
            prs.save(slide_path)

            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                zipf.write(outline_path, "Course_Outline.docx")
                zipf.write(guide_path, "Facilitator_Guide.docx")
                zipf.write(workbook_path, "Participant_Workbook.docx")
                zipf.write(quiz_path, "Quiz.docx")
                zipf.write(slide_path, "Slide_Deck.pptx")
            zip_buffer.seek(0)

            st.success("✅ All course materials generated successfully!")

            # Persistent download buttons
            st.download_button("📥 Download All Materials (ZIP)", data=zip_buffer, file_name="Course_Materials.zip", mime="application/zip")
            st.download_button("Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Participant Workbook", open(workbook_path, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", open(slide_path, "rb"), file_name="Slide_Deck.pptx")

        except Exception as e:
            st.error(f"Error generating content: {e}")
