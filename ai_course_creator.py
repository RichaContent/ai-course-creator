import streamlit as st
import openai
import os
import tempfile
import PyPDF2
import docx2txt
from pptx import Presentation
from pptx.util import Inches, Pt
from docx import Document
from io import BytesIO
import zipfile

# Load OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()
openai.api_key = api_key

st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# Course inputs
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience (e.g., Mid-Level Managers)")
duration = st.slider("Duration (in minutes)", 30, 300, 90, step=30)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# Optional references
st.header("Step 2 (Optional): Add References")
uploaded_files = st.file_uploader("Upload Reference Files (PDF, Word, PPT)", accept_multiple_files=True)
user_notes = st.text_area("Add Notes or Specific Requirements")

# Optional feedback
st.header("Step 3 (Optional): Feedback for Revisions")
feedback = st.text_area("Any feedback to revise the course (if applicable)?")

if st.button("Generate Course Materials"):
    with st.spinner("Generating course content..."):
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

        # Construct prompt
        prompt = f"""
        Create a {duration}-minute training course on the topic: "{topic}" for the audience: {audience}.
        Use a {tonality.lower()} tone.

        Include:
        - A course outline in table format (Time, Activity Type, Description)
        - A facilitator guide with clear instructions, key messages, definitions, case studies
        - A participant workbook with instructions, reflection prompts, activities
        - A quiz with MCQs, MMCQs, and True/False questions and an answer key
        - A slide deck in bullet format (one slide per outline point with relevant subpoints and explanations)
        {f"- Refer to these notes: {user_notes}" if user_notes else ""}
        {f"- Revise based on this feedback: {feedback}" if feedback else ""}
        {f"- Reference the following text: {extracted_text}" if extracted_text else ""}

        Clearly label outputs as Course_Outline, Facilitator_Guide, Workbook, Quiz, and Slides.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content

            # Parse output
            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Workbook": "", "Quiz": "", "Slides": ""}
            current = None
            for line in content.splitlines():
                for key in sections:
                    if key in line:
                        current = key
                        break
                else:
                    if current:
                        sections[current] += line + "\n"

            def save_doc(text, filename):
                doc = Document()
                for line in text.strip().splitlines():
                    doc.add_paragraph(line)
                path = os.path.join(tempfile.gettempdir(), filename)
                doc.save(path)
                return path

            def save_ppt(text, filename):
                prs = Presentation()
                for slide_text in text.strip().split("\n\n"):
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    lines = slide_text.strip().splitlines()
                    title = lines[0] if lines else ""
                    content = lines[1:] if len(lines) > 1 else []
                    slide.shapes.title.text = title
                    body_shape = slide.shapes.placeholders[1]
                    tf = body_shape.text_frame
                    for point in content:
                        tf.add_paragraph().text = point.strip()
                path = os.path.join(tempfile.gettempdir(), filename)
                prs.save(path)
                return path

            outline_path = save_doc(sections["Course_Outline"], "Course_Outline.docx")
            guide_path = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")
            workbook_path = save_doc(sections["Workbook"], "Participant_Workbook.docx")
            quiz_path = save_doc(sections["Quiz"], "Quiz.docx")
            slide_path = save_ppt(sections["Slides"], "Slide_Deck.pptx")

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                zipf.write(outline_path, "Course_Outline.docx")
                zipf.write(guide_path, "Facilitator_Guide.docx")
                zipf.write(workbook_path, "Participant_Workbook.docx")
                zipf.write(quiz_path, "Quiz.docx")
                zipf.write(slide_path, "Slide_Deck.pptx")
            zip_buffer.seek(0)

            st.success("Course materials generated successfully!")
            st.download_button("📥 Download All as ZIP", zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
            st.download_button("Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Workbook", open(workbook_path, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
            st.download_button("Slide Deck", open(slide_path, "rb"), file_name="Slide_Deck.pptx")

        except Exception as e:
            st.error(f"Error generating content: {e}")
