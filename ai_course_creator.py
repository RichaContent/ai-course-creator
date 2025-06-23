import streamlit as st
import openai
import os
import tempfile
import mammoth
import PyPDF2
import docx2txt
from pptx import Presentation
from pptx.util import Inches, Pt
from docx import Document
from io import BytesIO
from dotenv import load_dotenv
import zipfile
import json

# Load environment variables
load_dotenv()

# App Title
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# Load OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password", key="api_key")
if not api_key:
    st.warning("Please enter your OpenAI API key to proceed.")
    st.stop()
openai.api_key = api_key

# User Inputs
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic", key="topic")
audience = st.text_input("Target Audience (e.g., Mid-Level Managers)", key="audience")
duration = st.slider("Duration (in minutes)", 30, 300, 90, step=30, key="duration")
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"], key="tone")

# Optional Inputs
st.header("Step 2 (Optional): Add References")
uploaded_files = st.file_uploader("Upload Reference Files (PDF, Word, PPT)", accept_multiple_files=True)
user_notes = st.text_area("Add Notes or Specific Requirements")
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
            elif uploaded_file.name.endswith(".pptx"):
                ppt = Presentation(uploaded_file)
                for slide in ppt.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            extracted_text += shape.text + "\n"

        # Construct the prompt
        prompt = f"""
        Create a {duration}-minute training course on the topic: "{topic}" for the audience: {audience}.
        Use a {tonality.lower()} tone.
        Include:
        - A course outline in table format with timings and type of delivery (e.g., lecture, case study, role play)
        - A well-structured facilitator guide with session objectives, key messages, transitions, case studies, and explanations
        - A participant workbook with clear instructions, reflective exercises, role-play scenarios (not full scripts)
        - A quiz with a mix of MCQs, MMCQs, and True/False questions, including an answer key
        - A slide deck covering all key points, quotes, definitions, and visuals in bullet format
        {f"- Refer to these notes: {user_notes}" if user_notes else ""}
        {f"- Revise based on this feedback: {feedback}" if feedback else ""}
        {f"- Reference the following text: {extracted_text}" if extracted_text else ""}
        Return the content in structured JSON format with the keys: Course_Outline, Facilitator_Guide, Workbook, Quiz, Slide_Deck.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content

            data = json.loads(content)

            def save_doc(text, filename):
                doc = Document()
                for line in text.strip().splitlines():
                    doc.add_paragraph(line)
                path = os.path.join(tempfile.gettempdir(), filename)
                doc.save(path)
                return path

            def generate_ppt(slides, filename):
                prs = Presentation()
                for slide_data in slides:
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    title = slide.shapes.title
                    content_shape = slide.shapes.placeholders[1]
                    title.text = slide_data.get("title", "")
                    for bullet in slide_data.get("bullets", []):
                        p = content_shape.text_frame.add_paragraph()
                        p.text = bullet
                path = os.path.join(tempfile.gettempdir(), filename)
                prs.save(path)
                return path

            outline_path = save_doc(data["Course_Outline"], "Course_Outline.docx")
            guide_path = save_doc(data["Facilitator_Guide"], "Facilitator_Guide.docx")
            workbook_path = save_doc(data["Workbook"], "Participant_Workbook.docx")
            quiz_path = save_doc(data["Quiz"], "Quiz.docx")
            ppt_path = generate_ppt(data["Slide_Deck"], "Slide_Deck.pptx")

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
            st.download_button("Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Workbook", open(workbook_path, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", open(ppt_path, "rb"), file_name="Slide_Deck.pptx")

            tokens_used = response.usage.total_tokens
            cost_estimate = round(tokens_used / 1000 * 0.01, 4)
            st.caption(f"Used {tokens_used} tokens · Estimated cost: ${cost_estimate:.4f}")

        except Exception as e:
            st.error(f"Error generating content: {e}")
