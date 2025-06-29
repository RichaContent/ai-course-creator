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

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("📚 AI Course Creator for Trainers")

# Step 1: Course Details
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic", "Growth Mindset")
audience = st.text_input("Target Audience", "Middle Management")
duration = st.slider("Duration (minutes)", 30, 240, 90, step=15)
tone = st.selectbox("Tone of Voice", ["Professional", "Conversational", "Inspirational"])

# Step 2: Upload files and notes
st.header("Step 2: Upload Reference Files & Notes (Optional)")
uploaded_files = st.file_uploader("Upload PDF, DOCX, PPTX files", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
notes = st.text_area("Notes or Specific Instructions (Optional)")

# Step 3: Feedback for revision
st.header("Step 3: Feedback for Revision (Optional)")
feedback = st.text_area("Feedback for refinement (Optional)")

# File extraction
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
    return text[:8000]  # limit for token safety

# Slide deck generation
def generate_slide_deck(slide_content):
    prs = Presentation()
    for block in slide_content.strip().split("\n\n"):
        lines = block.strip().split("\n")
        if not lines:
            continue
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = lines[0]
        textbox = slide.placeholders[1]
        for bullet in lines[1:]:
            p = textbox.text_frame.add_paragraph()
            p.text = bullet
            p.font.size = Pt(20)
    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

# DOCX generation
def save_docx(content, filename):
    doc = Document()
    for line in content.strip().split("\n"):
        doc.add_paragraph(line)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(temp_path)
    return temp_path

# Generate button
if st.button("🚀 Generate Course Materials"):
    with st.spinner("Generating your comprehensive course materials..."):

        extracted_text = extract_uploaded_text(uploaded_files) if uploaded_files else ""
        ref_part = f"Reference Content:\n{extracted_text}\n" if extracted_text else ""
        notes_part = f"Notes:\n{notes}\n" if notes else ""
        feedback_part = f"Feedback for refinement:\n{feedback}\n" if feedback else ""

        prompt = f"""
You are a professional instructional designer creating a final delivery-ready training program.

Topic: {topic}
Audience: {audience}
Duration: {duration} minutes
Tone: {tone}

Requirements:
✅ Provide a **detailed, tabular Course Outline** with columns: Time, Activity Type, Explicit Description.
✅ Create a **Facilitator Guide** with:
- Exact instructions on what to say
- Step-by-step flow
- Definitions explained in simple terms
- Public domain references only
- Case study examples (fully included)
- Instructions on handling participant questions.

✅ Create a **Participant Workbook** with:
- Reflection activities
- Actionable exercises
- Explicit instructions for each section
- Scenarios and role-plays (with scenario text).

✅ Create a **Quiz** with:
- 5-8 questions (MCQ, MMCQ, T/F)
- Correct answers clearly indicated
- Aligned with the course objectives.

✅ Create a **Slide Deck** with:
- Complete titles and bullet points
- Practical tips
- Definitions
- Quotes only if public domain.

✅ All content must be fully usable by **non-SME trainers without additional editing**.

✅ If feedback is provided, incorporate it while maintaining previous content.

{ref_part}
{notes_part}
{feedback_part}

Return the output in sections:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
"""

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-preview",
                messages=[
                    {"role": "system", "content": "You are a precise, clear instructional designer generating final delivery materials."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_content = completion.choices[0].message.content

            sections = {key: "" for key in ["COURSE_OUTLINE", "FACILITATOR_GUIDE", "PARTICIPANT_WORKBOOK", "QUIZ", "SLIDE_DECK"]}
            current_section = None
            for line in response_content.splitlines():
                line = line.strip()
                if line.startswith("## ") and line[3:] in sections:
                    current_section = line[3:]
                elif current_section:
                    sections[current_section] += line + "\n"

            # Save DOCX
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

            # Downloads
            st.success("✅ All materials generated successfully!")
            st.download_button("📥 Download All as ZIP", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(outline_file, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_file, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Workbook", open(workbook_file, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_file, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", slide_deck_file, file_name="Slide_Deck.pptx")

            # Token and cost tracking
            try:
                tokens_used = completion.usage.total_tokens
                cost_estimate = round(tokens_used / 1000 * 0.03, 4)  # adjust rate if needed
                st.caption(f"Used {tokens_used} tokens · Estimated cost: ${cost_estimate:.4f}")
            except:
                pass

        except Exception as e:
            st.error(f"❌ Error generating content: {e}")
