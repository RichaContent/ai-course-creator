import streamlit as st
import os
from openai import OpenAI
from pptx import Presentation
from pptx.util import Pt
from io import BytesIO
from docx import Document
import tempfile
import PyPDF2
import docx2txt
import zipfile

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Streamlit page setup
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("📚 AI Course Creator for Trainers")

# User Inputs
st.header("Step 1: Enter Course Details")
topic = st.text_input("Course Topic", "")
audience = st.text_input("Target Audience", "Mid-Level Managers")
duration = st.slider("Course Duration (minutes)", 30, 240, 90, step=15)
level = st.selectbox("Course Level", ["Beginner", "Intermediate", "Advanced"])
tone = st.selectbox("Preferred Tone", ["Professional", "Conversational", "Inspirational"])

# Optional Notes
notes = st.text_area("Add Notes or Specific Instructions (Optional)")

# Upload Files
uploaded_files = st.file_uploader("Upload Reference Files (PDF, DOCX, PPTX) (Optional)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)

# Feedback
feedback = st.text_area("Feedback for Refinement (Optional)")

# Extract text from uploaded files
def extract_uploaded_text(files):
    text = ""
    for file in files:
        if file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif file.name.endswith(".docx"):
            text += docx2txt.process(file) + "\n"
        elif file.name.endswith(".pptx"):
            ppt = Presentation(file)
            for slide in ppt.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
    return text[:8000]

# Generate slide deck
def generate_slide_deck(content):
    prs = Presentation()
    for block in content.strip().split("\n\n"):
        lines = block.strip().split("\n")
        if lines:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = lines[0]
            textbox = slide.placeholders[1]
            for bullet in lines[1:]:
                p = textbox.text_frame.add_paragraph()
                p.text = bullet
                p.font.size = Pt(20)
    output = BytesIO()
    prs.save(output)
    output.seek(0)
    return output

# Generate DOCX
def save_docx(content, filename):
    doc = Document()
    for line in content.strip().split("\n"):
        doc.add_paragraph(line)
    path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(path)
    return path

# Generate Button
if st.button("🚀 Generate Course Materials"):
    with st.spinner("Generating your course materials..."):

        extracted_text = extract_uploaded_text(uploaded_files) if uploaded_files else ""

        prompt = f"""
You are a professional instructional designer creating a delivery-ready course.

Topic: {topic}
Audience: {audience}
Duration: {duration} minutes
Level: {level}
Tone: {tone}

Requirements:
✅ Tabular Course Outline (Time, Activity, Description).
✅ Detailed Facilitator Guide with instructions, explanations, and public domain references only.
✅ Participant Workbook with clear instructions, exercises, and reflective activities.
✅ Quiz with 5-8 MCQs/MMCQs/True-False with correct answers.
✅ Slide Deck with clear titles and bullet points aligned with the course.

{f"Notes:\n{notes}" if notes else ""}
{f"Feedback for refinement:\n{feedback}" if feedback else ""}
{f"Reference Content:\n{extracted_text}" if extracted_text else ""}

Return output in sections:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
"""

        try:
            try:
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a precise instructional designer generating delivery-ready corporate training materials."},
                        {"role": "user", "content": prompt}
                    ]
                )
            except Exception:
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a precise instructional designer generating delivery-ready corporate training materials."},
                        {"role": "user", "content": prompt}
                    ]
                )

            response = completion.choices[0].message.content
            sections = {k: "" for k in ["COURSE_OUTLINE", "FACILITATOR_GUIDE", "PARTICIPANT_WORKBOOK", "QUIZ", "SLIDE_DECK"]}
            current = None
            for line in response.splitlines():
                line = line.strip()
                if line.startswith("## ") and line[3:] in sections:
                    current = line[3:]
                elif current:
                    sections[current] += line + "\n"

            # Generate files
            outline_file = save_docx(sections["COURSE_OUTLINE"], "Course_Outline.docx")
            guide_file = save_docx(sections["FACILITATOR_GUIDE"], "Facilitator_Guide.docx")
            workbook_file = save_docx(sections["PARTICIPANT_WORKBOOK"], "Participant_Workbook.docx")
            quiz_file = save_docx(sections["QUIZ"], "Quiz.docx")
            slide_deck_file = generate_slide_deck(sections["SLIDE_DECK"])

            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                zf.write(outline_file, "Course_Outline.docx")
                zf.write(guide_file, "Facilitator_Guide.docx")
                zf.write(workbook_file, "Participant_Workbook.docx")
                zf.write(quiz_file, "Quiz.docx")
                zf.writestr("Slide_Deck.pptx", slide_deck_file.getvalue())
            zip_buffer.seek(0)

            # Download buttons
            st.success("✅ Course materials generated successfully!")
            st.download_button("📥 Download All Materials (ZIP)", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(outline_file, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_file, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Participant Workbook", open(workbook_file, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_file, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", slide_deck_file, file_name="Slide_Deck.pptx")

            # Token usage and cost
            try:
                tokens_used = completion.usage.total_tokens
                cost_estimate = round(tokens_used / 1000 * 0.03, 4)
                st.caption(f"Used {tokens_used} tokens · Estimated cost: ${cost_estimate:.4f}")
            except:
                pass

        except Exception as e:
            st.error(f"❌ Error generating content: {e}")
