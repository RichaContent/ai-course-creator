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
st.title("📚 AI Course Creator")

# Step 1: Course Details
st.header("Step 1: Course Details")
topic = st.text_input("Course Topic", "Growth Mindset")
audience = st.text_input("Target Audience", "Middle Management")
duration = st.slider("Duration (minutes)", 30, 240, 90, step=15)
tone = st.selectbox("Tone of Voice", ["Professional", "Conversational", "Inspirational"])

# Step 2: Upload files and notes
st.header("Step 2: Upload Reference Files & Notes (Optional)")
uploaded_files = st.file_uploader("Upload PDF, DOCX, PPTX files", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
notes = st.text_area("Notes or Special Instructions (Optional)")

# Step 3: Feedback
st.header("Step 3: Feedback for Revisions (Optional)")
feedback = st.text_area("Feedback (Optional)")

# File extraction function
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
    return text[:8000]  # trim for token safety

# Slide deck generator
def generate_slide_deck(slide_text_blocks):
    prs = Presentation()
    for block in slide_text_blocks.strip().split("\n\n"):
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

# DOCX saver
def save_docx(text, filename):
    doc = Document()
    for line in text.strip().split("\n"):
        doc.add_paragraph(line)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(temp_path)
    return temp_path

# Generate
if st.button("🚀 Generate Course Materials"):
    with st.spinner("Generating high-quality course materials..."):

        extracted_text = extract_uploaded_text(uploaded_files) if uploaded_files else ""
        reference_part = f"Reference Content:\n{extracted_text}\n" if extracted_text else ""
        notes_part = f"Notes:\n{notes}\n" if notes else ""
        feedback_part = f"Feedback:\n{feedback}\n" if feedback else ""

        prompt = f"""
You are an expert instructional designer.

Create a ready-to-deliver, content-rich corporate training on "{topic}" for "{audience}", duration {duration} minutes, tone: {tone}.

Requirements:
1️⃣ A detailed **tabular Course Outline** with columns: Time, Activity Type, Detailed Description.
2️⃣ A **Facilitator Guide** with researched definitions, real quotes, case studies, and practical examples.
3️⃣ A **Participant Workbook** with actionable reflection activities and exercises.
4️⃣ A **Quiz** with 5-8 MCQs, MMCQs, True/False questions, and an answer key.
5️⃣ A **Slide Deck** with complete content on each slide (titles and bullet points), including quotes and examples, ready for delivery.

{reference_part}
{notes_part}
{feedback_part}

Return outputs in sections:
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
                    {"role": "system", "content": "You are a professional instructional designer."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_content = completion.choices[0].message.content

            sections = {
                "COURSE_OUTLINE": "",
                "FACILITATOR_GUIDE": "",
                "PARTICIPANT_WORKBOOK": "",
                "QUIZ": "",
                "SLIDE_DECK": ""
            }

            current_section = None
            for line in response_content.splitlines():
                line = line.strip()
                if line.startswith("## ") and line[3:] in sections:
                    current_section = line[3:]
                elif current_section:
                    sections[current_section] += line + "\n"

            # Save files
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

            # Display downloads
            st.success("✅ Course materials generated successfully!")
            st.download_button("📥 Download All Materials (ZIP)", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(outline_file, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_file, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Workbook", open(workbook_file, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_file, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", slide_deck_file, file_name="Slide_Deck.pptx")

            # Show tokens used
            try:
                tokens_used = completion.usage.total_tokens
                cost = tokens_used / 1000 * 0.01
                st.caption(f"Used {tokens_used} tokens. Estimated cost: ${cost:.4f}")
            except:
                pass

        except Exception as e:
            st.error(f"❌ Error generating content: {e}")
