import streamlit as st
import os
import tempfile
import openai
from openai import OpenAI
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from io import BytesIO
import zipfile
from dotenv import load_dotenv
import PyPDF2
import docx2txt
from typing import Dict

# Load .env if available
load_dotenv()

# --- Streamlit UI Setup ---
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# --- Load OpenAI API Key ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()

client = OpenAI(api_key=api_key)

# --- User Inputs ---
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience (e.g., Mid-Level Managers)")
duration = st.slider("Duration (in minutes)", 30, 300, 90, step=30)
tonality = st.selectbox("Preferred Tonality", ["Professional", "Conversational", "Inspirational", "Academic"])

# --- Optional Uploads ---
st.header("Step 2 (Optional): Reference Files and Notes")
uploaded_files = st.file_uploader("Upload Reference Files (PDF, Word, PPT)", accept_multiple_files=True)
user_notes = st.text_area("Add Notes or Specific Requirements")
feedback = st.text_area("Feedback for Revisions")

# --- Helper to Extract Text ---
def extract_text(files):
    text = ""
    for file in files:
        if file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif file.name.endswith(".docx"):
            text += docx2txt.process(file)
        elif file.name.endswith(".pptx"):
            prs = Presentation(file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
    return text

# --- Helper to Save DOCX ---
def save_doc(content, filename):
    doc = Document()
    for line in content.strip().splitlines():
        doc.add_paragraph(line)
    path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(path)
    return path

# --- Helper to Save PPTX ---
def save_ppt(slides_text, filename):
    prs = Presentation()
    for block in slides_text.strip().split("\n\n"):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title, *points = block.strip().split("\n")
        slide.shapes.title.text = title.strip()
        content = slide.shapes.placeholders[1].text_frame
        for point in points:
            para = content.add_paragraph()
            para.text = point.strip()
    path = os.path.join(tempfile.gettempdir(), filename)
    prs.save(path)
    return path

# --- Generate Button ---
if st.button("Generate Course Materials"):
    with st.spinner("Generating with GPT..."):
        ref_text = extract_text(uploaded_files) if uploaded_files else ""
        prompt = f"""
        You are an expert instructional designer.
        Create a {duration}-minute course on: "{topic}" for the audience: {audience}.
        Use a {tonality.lower()} tone.

        Include:
        - A course outline in table format with columns: Time, Topic, Activity Type (e.g., Lecture, Case, Role Play)
        - A detailed facilitator guide with examples, explanations, and notes for delivery
        - A participant workbook with reflection, exercises, space to write answers, and role play prompts
        - A quiz with MCQ, MMCQ, and True/False questions and answers
        - A slide deck with 1 slide per topic point, with definitions or subpoints as bullet points

        {f"Incorporate these notes: {user_notes}" if user_notes else ""}
        {f"Revise based on: {feedback}" if feedback else ""}
        {f"Reference this content: {ref_text}" if ref_text else ""}

        Return sections with headings: Course_Outline, Facilitator_Guide, Workbook, Quiz, Slides.
        """

        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            output = completion.choices[0].message.content

            # --- Parse sections ---
            parts: Dict[str, str] = {"Course_Outline": "", "Facilitator_Guide": "", "Workbook": "", "Quiz": "", "Slides": ""}
            current = None
            for line in output.splitlines():
                for key in parts:
                    if key in line:
                        current = key
                if current:
                    parts[current] += line + "\n"

            # --- Save files ---
            outline_path = save_doc(parts["Course_Outline"], "Course_Outline.docx")
            guide_path = save_doc(parts["Facilitator_Guide"], "Facilitator_Guide.docx")
            workbook_path = save_doc(parts["Workbook"], "Participant_Workbook.docx")
            quiz_path = save_doc(parts["Quiz"], "Quiz.docx")
            slide_path = save_ppt(parts["Slides"], "Slide_Deck.pptx")

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                zipf.write(outline_path, "Course_Outline.docx")
                zipf.write(guide_path, "Facilitator_Guide.docx")
                zipf.write(workbook_path, "Participant_Workbook.docx")
                zipf.write(quiz_path, "Quiz.docx")
                zipf.write(slide_path, "Slide_Deck.pptx")

            zip_buffer.seek(0)
            st.success("✅ Course materials generated successfully!")

            st.download_button("📥 Download All as ZIP", zip_buffer, file_name="Course_Materials.zip")
            with open(outline_path, "rb") as f:
                st.download_button("📄 Download Course Outline", f, file_name="Course_Outline.docx")
            with open(guide_path, "rb") as f:
                st.download_button("📄 Download Facilitator Guide", f, file_name="Facilitator_Guide.docx")
            with open(workbook_path, "rb") as f:
                st.download_button("📄 Download Workbook", f, file_name="Participant_Workbook.docx")
            with open(quiz_path, "rb") as f:
                st.download_button("📄 Download Quiz", f, file_name="Quiz.docx")
            with open(slide_path, "rb") as f:
                st.download_button("📊 Download Slide Deck", f, file_name="Slide_Deck.pptx")

            # Token info
            if completion.usage:
                tokens = completion.usage.total_tokens
                cost = round(tokens / 1000 * 0.01, 4)
                st.caption(f"Used {tokens} tokens · Estimated cost: ${cost:.4f}")

        except Exception as e:
            st.error(f"Error generating content: {e}")
