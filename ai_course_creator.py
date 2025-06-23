import streamlit as st
import openai
import os
import tempfile
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.dml.color import RGBColor
from docx import Document
from dotenv import load_dotenv
from io import BytesIO
import zipfile
import PyPDF2
import docx2txt

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# User Inputs
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience")
duration = st.slider("Duration (in minutes)", 30, 300, 90, step=30)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# Optional Inputs
st.header("Step 2 (Optional): Add References")
uploaded_files = st.file_uploader("Upload Reference Files (PDF, Word, PPT)", accept_multiple_files=True)
user_notes = st.text_area("Add Notes or Specific Requirements")

# Feedback
st.header("Step 3 (Optional): Feedback for Revisions")
feedback = st.text_area("Any feedback to revise the course (if applicable)?")

if st.button("Generate Course Materials"):
    with st.spinner("Generating course content..."):

        # Extract uploaded content
        extracted_text = ""
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith(".pdf"):
                reader = PyPDF2.PdfReader(uploaded_file)
                extracted_text += "\n".join([page.extract_text() or '' for page in reader.pages])
            elif uploaded_file.name.endswith(".docx"):
                extracted_text += docx2txt.process(uploaded_file)

        # Prompt
        prompt = f"""
        Create a {duration}-minute corporate training course on the topic: "{topic}" for the audience: {audience}.
        Use a {tonality.lower()} tone. Include:
        1. Course Outline in table format with columns Time | Activity Type | Description
        2. Facilitator Guide with session objectives, instructions, transitions.
        3. Workbook with instructions, reflections, and exercises.
        4. Quiz with MCQs, MMCQs, True/False, and answer key.
        5. Slide deck content: one slide per course outline row, include bullet points, quotes, definitions.
        {f"6. Incorporate user notes: {user_notes}" if user_notes else ""}
        {f"7. Revise per feedback: {feedback}" if feedback else ""}
        {f"8. Reference text: {extracted_text}" if extracted_text else ""}
        Return each section clearly marked as:
        <Course_Outline> ... </Course_Outline>
        <Facilitator_Guide> ... </Facilitator_Guide>
        <Workbook> ... </Workbook>
        <Quiz> ... </Quiz>
        <Slide_Deck> ... </Slide_Deck>
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content

            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Workbook": "", "Quiz": "", "Slide_Deck": ""}
            current = None
            for line in content.splitlines():
                tag_open = next((tag for tag in sections if f"<{tag}>" in line), None)
                tag_close = next((tag for tag in sections if f"</{tag}>" in line), None)
                if tag_open:
                    current = tag_open
                    continue
                elif tag_close:
                    current = None
                    continue
                elif current:
                    sections[current] += line + "\n"

            def save_doc(text, filename):
                doc = Document()
                for line in text.strip().splitlines():
                    doc.add_paragraph(line)
                path = os.path.join(tempfile.gettempdir(), filename)
                doc.save(path)
                return path

            # Save documents
            outline_path = save_doc(sections["Course_Outline"], "Course_Outline.docx")
            guide_path = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")
            workbook_path = save_doc(sections["Workbook"], "Participant_Workbook.docx")
            quiz_path = save_doc(sections["Quiz"], "Quiz.docx")

            # Generate slide deck
            ppt = Presentation()
            for slide_text in sections["Slide_Deck"].strip().split("\n\n"):
                slide = ppt.slides.add_slide(ppt.slide_layouts[1])
                lines = slide_text.splitlines()
                if not lines:
                    continue
                title, bullets = lines[0], lines[1:]
                slide.shapes.title.text = title.strip()
                content_box = slide.placeholders[1]
                tf = content_box.text_frame
                tf.clear()
                for bullet in bullets:
                    tf.add_paragraph().text = bullet.strip("- ")
            ppt_path = os.path.join(tempfile.gettempdir(), "Slide_Deck.pptx")
            ppt.save(ppt_path)

            # Zip
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                zip_file.write(outline_path, "Course_Outline.docx")
                zip_file.write(guide_path, "Facilitator_Guide.docx")
                zip_file.write(workbook_path, "Participant_Workbook.docx")
                zip_file.write(quiz_path, "Quiz.docx")
                zip_file.write(ppt_path, "Slide_Deck.pptx")
            zip_buffer.seek(0)

            st.success("Course materials generated successfully!")
            st.download_button("📥 Download All as ZIP", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(outline_path, "rb"))
            st.download_button("Download Facilitator Guide", open(guide_path, "rb"))
            st.download_button("Download Workbook", open(workbook_path, "rb"))
            st.download_button("Download Quiz", open(quiz_path, "rb"))
            st.download_button("Download Slide Deck", open(ppt_path, "rb"))

        except Exception as e:
            st.error(f"An error occurred: {e}")
