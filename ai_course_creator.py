import streamlit as st
import openai
import os
import tempfile
import docx2txt
import PyPDF2
import mammoth
from pptx import Presentation
from docx import Document
from io import BytesIO
from dotenv import load_dotenv
import zipfile

# Load environment variables
load_dotenv()

# App config
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# Load OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()
openai.api_key = api_key

# Course Inputs
st.header("Step 1: Course Inputs")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience")
duration = st.slider("Duration (in minutes)", 30, 300, 90, step=30)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# Optional Inputs
st.header("Step 2 (Optional): Add Reference Material")
uploaded_files = st.file_uploader("Upload Reference Files (PDF, DOCX, PPTX)", accept_multiple_files=True)
user_notes = st.text_area("Add any notes or instructions")
feedback = st.text_area("Suggest any feedback or revisions")

# Extract text from files
def extract_text(files):
    combined_text = ""
    for file in files:
        if file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                combined_text += page.extract_text() or ""
        elif file.name.endswith(".docx"):
            combined_text += docx2txt.process(file)
        elif file.name.endswith(".pptx"):
            ppt = Presentation(file)
            for slide in ppt.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        combined_text += shape.text + "\n"
    return combined_text

# Save DOCX helper
def save_doc(content, filename):
    doc = Document()
    for line in content.strip().splitlines():
        doc.add_paragraph(line)
    path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(path)
    return path

# Save PPTX helper
def save_pptx(slides_data):
    ppt = Presentation()
    for slide_text in slides_data.strip().split("\n\n"):
        slide = ppt.slides.add_slide(ppt.slide_layouts[1])
        title, *bullets = slide_text.strip().split("\n")
        slide.shapes.title.text = title
        content = slide.placeholders[1].text_frame
        for bullet in bullets:
            content.add_paragraph(bullet.strip())
    path = os.path.join(tempfile.gettempdir(), "Slide_Deck.pptx")
    ppt.save(path)
    return path

# Generate course
if st.button("Generate Course Materials"):
    with st.spinner("Generating content..."):
        ref_text = extract_text(uploaded_files) if uploaded_files else ""

        prompt = f"""
        Create a {duration}-minute training course on the topic: "{topic}" for the audience: {audience}.
        Use a {tonality.lower()} tone.

        Include the following:
        1. A tabular course outline with columns for Time, Topic, and Method (lecture, case study, etc.)
        2. A facilitator guide with learning objectives, definitions, case study outlines, key points, and transitions
        3. A participant workbook written in second person with reflective activities, space for notes, and role-play scenarios
        4. A quiz with MCQs, MMCQs, and True/False questions, including correct answers clearly indicated
        5. A slide deck with one slide per concept, including quote, definition, bullet points

        {f"Use this reference text: {ref_text}" if ref_text else ""}
        {f"Consider these notes: {user_notes}" if user_notes else ""}
        {f"Incorporate feedback: {feedback}" if feedback else ""}

        Return output clearly marked as:
        Course_Outline:
        Facilitator_Guide:
        Participant_Workbook:
        Quiz:
        Slide_Deck:
        """

        try:
            rsp = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            content = rsp.choices[0].message.content
            tokens_used = rsp.usage.total_tokens
            cost_estimate = round(tokens_used / 1000 * 0.01, 4)

            sections = {"Course_Outline": "", "Facilitator_Guide": "", "Participant_Workbook": "", "Quiz": "", "Slide_Deck": ""}
            current = None
            for line in content.splitlines():
                for key in sections:
                    if key + ":" in line:
                        current = key
                        break
                else:
                    if current:
                        sections[current] += line + "\n"

            # Save files
            files = {}
            files["Course_Outline.docx"] = save_doc(sections["Course_Outline"], "Course_Outline.docx")
            files["Facilitator_Guide.docx"] = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")
            files["Participant_Workbook.docx"] = save_doc(sections["Participant_Workbook"], "Participant_Workbook.docx")
            files["Quiz.docx"] = save_doc(sections["Quiz"], "Quiz.docx")
            files["Slide_Deck.pptx"] = save_pptx(sections["Slide_Deck"])

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for fname, fpath in files.items():
                    zipf.write(fpath, fname)
            zip_buffer.seek(0)

            st.success("Course materials generated!")
            st.download_button("📦 Download All (ZIP)", data=zip_buffer, file_name="Course_Materials.zip")
            for fname, fpath in files.items():
                st.download_button(f"Download {fname}", data=open(fpath, "rb"), file_name=fname)
            st.caption(f"Used {tokens_used} tokens · Estimated cost: ${cost_estimate}")

        except Exception as e:
            st.error(f"Error generating content: {e}")
