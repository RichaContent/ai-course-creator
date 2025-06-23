import os
import streamlit as st
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
from docx import Document
import PyPDF2
import docx2txt
from pptx import Presentation
from io import BytesIO
import zipfile
import tempfile

# Set page config
st.set_page_config(page_title="AI Course Creator")

# Load API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password")

if not api_key:
    st.stop()

client = OpenAI(api_key=api_key)

st.title("📚 AI Course Creator")

# User Inputs
st.header("Step 1: Course Inputs")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience")
duration = st.slider("Course Duration (in minutes)", 30, 300, 90)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# Optional
st.header("Step 2: Optional Inputs")
uploaded_files = st.file_uploader("Upload Reference Files (PDF, Word, PPT)", accept_multiple_files=True)
user_notes = st.text_area("Your Notes for Customization")
feedback = st.text_area("Any Feedback on Previous Course Version")

if st.button("Generate Course Materials"):
    with st.spinner("Generating content..."):

        # Extract text from uploaded files
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

        # Prompt
        prompt = f"""
Create a {duration}-minute training course titled '{topic}' for the audience: {audience}.
Use a {tonality.lower()} tone.

Include the following:
1. A Course_Outline in **tabular format** with timing, content, delivery mode.
2. A rich Facilitator_Guide with key messages, facilitation instructions, case studies, transitions, and definitions.
3. A Workbook for participants with instructions, activities, reflection prompts, and role-play scenarios.
4. A Quiz with MCQ, MMCQ, and True/False questions and an answer key.
5. A Slide_Deck: Each slide should have a title, 2–3 bullet points and any quotes, definitions or examples.

{f"- Incorporate the following user notes: {user_notes}" if user_notes else ""}
{f"- Revise the content based on this feedback: {feedback}" if feedback else ""}
{f"- Reference this material: {extracted_text[:2000]}" if extracted_text else ""}

Respond using distinct sections titled:
Course_Outline
Facilitator_Guide
Participant_Workbook
Quiz
Slide_Deck
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            output = response.choices[0].message.content

            # Parse response
            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Participant_Workbook": "", "Quiz": "", "Slide_Deck": ""}
            current = None
            for line in output.splitlines():
                header = line.strip().replace(" ", "_")
                if header in sections:
                    current = header
                elif current:
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
                for slide_block in text.strip().split("\n\n"):
                    lines = slide_block.strip().split("\n")
                    if not lines: continue
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    slide.shapes.title.text = lines[0]
                    for bullet in lines[1:]:
                        if bullet.strip():
                            slide.shapes.placeholders[1].text += f"\n{bullet}"
                path = os.path.join(tempfile.gettempdir(), filename)
                prs.save(path)
                return path

            outline_path = save_doc(sections["Course_Outline"], "Course_Outline.docx")
            guide_path = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")
            workbook_path = save_doc(sections["Participant_Workbook"], "Participant_Workbook.docx")
            quiz_path = save_doc(sections["Quiz"], "Quiz.docx")
            slide_path = save_ppt(sections["Slide_Deck"], "Slide_Deck.pptx")

            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                zip_file.write(outline_path, "Course_Outline.docx")
                zip_file.write(guide_path, "Facilitator_Guide.docx")
                zip_file.write(workbook_path, "Participant_Workbook.docx")
                zip_file.write(quiz_path, "Quiz.docx")
                zip_file.write(slide_path, "Slide_Deck.pptx")
            zip_buffer.seek(0)

            # Success and Downloads
            st.success("✅ Course materials generated!")

            st.download_button("📥 Download All as ZIP", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Participant Workbook", open(workbook_path, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", open(slide_path, "rb"), file_name="Slide_Deck.pptx")

            # Token usage
            usage = response.usage.total_tokens
            cost = round(usage / 1000 * 0.01, 4)
            st.caption(f"Used {usage} tokens · Estimated cost: ${cost:.4f}")

        except Exception as e:
            st.error(f"Error generating content: {e}")
