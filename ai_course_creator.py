# AI Course Creator - Final Streamlit Script with All Features

import streamlit as st
import openai
import os
import tempfile
from io import BytesIO
import zipfile
import mammoth
import PyPDF2
import docx2txt
from pptx import Presentation
from docx import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up page
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# API Key handling
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API Key to proceed.")
        st.stop()
openai.api_key = api_key

# User Inputs
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience")
duration = st.slider("Course Duration (minutes)", 30, 300, 90, step=30)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# Optional Inputs
st.header("Step 2 (Optional): Add Reference Files or Notes")
uploaded_files = st.file_uploader("Upload reference files (PDF, Word, PPT)", accept_multiple_files=True)
user_notes = st.text_area("Your Notes or Suggestions")
feedback = st.text_area("Feedback for Revisions (optional)")

# Generate course button
if st.button("Generate Course Materials"):
    with st.spinner("Generating content..."):

        extracted_text = ""
        for file in uploaded_files:
            if file.name.endswith(".pdf"):
                reader = PyPDF2.PdfReader(file)
                extracted_text += "\n".join([page.extract_text() or '' for page in reader.pages])
            elif file.name.endswith(".docx"):
                extracted_text += docx2txt.process(file)
            elif file.name.endswith(".pptx"):
                ppt = Presentation(file)
                for slide in ppt.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            extracted_text += shape.text + "\n"

        prompt = f'''
        Create a {duration}-minute training course on "{topic}" for {audience}.
        Tone: {tonality}.

        Deliverables:
        1. Course_Outline: Tabular format with time allocations and delivery method (e.g., lecture, role play, case study).
        2. Facilitator_Guide: Objectives, transitions, instructions, sample debriefs.
        3. Participant_Workbook: Reflective prompts, space for responses, instructions in second person.
        4. Quiz: 5 MCQs, 2 MMCQs (multiple correct), 3 True/False with answer key.
        5. Slide_Deck: 1 slide per key idea.
        {f"Include these notes: {user_notes}" if user_notes else ""}
        {f"Revise with this feedback: {feedback}" if feedback else ""}
        {f"Incorporate these references: {extracted_text}" if extracted_text else ""}

        Return each section clearly marked with headers: ### Course_Outline, ### Facilitator_Guide, ### Participant_Workbook, ### Quiz, ### Slide_Deck.
        '''

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content

            # Parse output
            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Participant_Workbook": "", "Quiz": "", "Slide_Deck": ""}
            current = None
            for line in content.splitlines():
                for key in sections:
                    if f"### {key}" in line:
                        current = key
                        break
                else:
                    if current:
                        sections[current] += line + "\n"

            # Save Word files
            def save_doc(name, text):
                doc = Document()
                for line in text.strip().splitlines():
                    doc.add_paragraph(line)
                path = os.path.join(tempfile.gettempdir(), name)
                doc.save(path)
                return path

            paths = {}
            paths['outline'] = save_doc("Course_Outline.docx", sections["Course_Outline"])
            paths['guide'] = save_doc("Facilitator_Guide.docx", sections["Facilitator_Guide"])
            paths['workbook'] = save_doc("Participant_Workbook.docx", sections["Participant_Workbook"])
            paths['quiz'] = save_doc("Quiz.docx", sections["Quiz"])

            # Create slide deck
            ppt = Presentation()
            for line in sections['Slide_Deck'].split('\n'):
                if line.strip():
                    slide = ppt.slides.add_slide(ppt.slide_layouts[1])
                    slide.shapes.title.text = topic
                    slide.placeholders[1].text = line.strip()
            ppt_path = os.path.join(tempfile.gettempdir(), "Slide_Deck.pptx")
            ppt.save(ppt_path)
            paths['slides'] = ppt_path

            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as z:
                for label, path in paths.items():
                    z.write(path, os.path.basename(path))
            zip_buffer.seek(0)

            st.success("✅ Course materials generated!")

            # Previews (limited)
            st.subheader("Preview")
            st.text_area("Course Outline", sections["Course_Outline"], height=200)
            st.text_area("Quiz", sections["Quiz"], height=200)

            # Downloads
            st.download_button("📥 Download All as ZIP", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(paths['outline'], "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(paths['guide'], "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Workbook", open(paths['workbook'], "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(paths['quiz'], "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", open(paths['slides'], "rb"), file_name="Slide_Deck.pptx")

            # Token use
            if hasattr(response, "usage"):
                tokens_used = response.usage.total_tokens
                cost_est = round(tokens_used / 1000 * 0.01, 4)
                st.caption(f"Used {tokens_used} tokens. Estimated cost: ${cost_est:.4f}")

        except Exception as e:
            st.error(f"Error: {e}")
