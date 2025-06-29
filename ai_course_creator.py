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

# Built-in prompt templates
templates = {
    "Leadership": """You are an expert instructional designer.
Create a delivery-ready, 90-minute training course on "Effective Leadership for First-Time Managers" for an audience of new managers.
Requirements:
✅ Tabular Course Outline (Time | Activity | Description).
✅ Detailed Facilitator Guide with practical instructions, public domain definitions, examples.
✅ Participant Workbook with reflective activities and exercises.
✅ Quiz (5-8 questions with answers).
✅ Slide Deck with clear titles and bullet points.
✅ Public domain references only, no placeholders.
✅ Practical examples, real scenarios.
✅ Tone: Professional yet engaging.
If notes or feedback are provided, integrate them while maintaining consistency.
Return sections:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
""",
    "Time Management": """You are an expert instructional designer.
Create a delivery-ready, 60-minute training course on "Time Management for Busy Professionals."
Requirements:
✅ Tabular Course Outline.
✅ Facilitator Guide with detailed talking points, examples.
✅ Participant Workbook with practical activities (prioritization, Eisenhower Matrix).
✅ Quiz with 5-8 aligned questions and answers.
✅ Slide Deck with actionable tips, examples, and reflection prompts.
✅ Clear, jargon-free, public domain references only.
✅ Practical case studies included.
If notes or feedback are provided, integrate them seamlessly.
Return sections:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
""",
    "Feedback & Performance Management": """You are an expert instructional designer.
Create a delivery-ready, 90-minute training course on "Feedback and Performance Management for Middle Managers."
Requirements:
✅ Tabular Course Outline.
✅ Detailed Facilitator Guide with sample dialogues, scenarios, SBIS model explanation.
✅ Participant Workbook with exercises on preparing feedback, role-plays.
✅ Quiz with practical scenario-based questions and answers.
✅ Slide Deck aligned to the course flow.
✅ All examples and quotes should be from public domain or generalized.
If notes or uploaded files are provided, incorporate them while maintaining previous structure.
Return sections:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
""",
    "Emotional Intelligence": """You are an expert instructional designer.
Create a delivery-ready, 90-minute training course on "Emotional Intelligence in the Workplace."
Requirements:
✅ Tabular Course Outline.
✅ Facilitator Guide with explanations of self-awareness, self-regulation, empathy, etc.
✅ Participant Workbook with reflection logs, activities.
✅ Quiz aligned with objectives, with answers.
✅ Slide Deck with clear visuals, definitions, and practical applications.
✅ Public domain references, no placeholders.
If notes or feedback are provided, incorporate while retaining structure.
Return sections:
## COURSE_OUTLINE
## FACILITATOR_GUIDE
## PARTICIPANT_WORKBOOK
## QUIZ
## SLIDE_DECK
"""
}

# Step 1: Select template
st.header("Step 1: Select Training Topic")
selected_template = st.selectbox("Choose a Course Template", list(templates.keys()))

# Optional custom notes
notes = st.text_area("Add Notes or Specific Instructions (Optional)")

# Step 2: Upload files
uploaded_files = st.file_uploader("Upload Reference Files (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)

# Step 3: Feedback
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

# Helper: Generate Slide Deck
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

# Helper: Save DOCX
def save_docx(content, filename):
    doc = Document()
    for line in content.strip().split("\n"):
        doc.add_paragraph(line)
    path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(path)
    return path

# Generate
if st.button("🚀 Generate Course Materials"):
    with st.spinner("Generating your complete course package..."):

        extracted_text = extract_uploaded_text(uploaded_files) if uploaded_files else ""
        prompt = templates[selected_template]
        if notes:
            prompt += f"\nNotes for customization:\n{notes}"
        if feedback:
            prompt += f"\nFeedback for refinement:\n{feedback}"
        if extracted_text:
            prompt += f"\nReference extracted content:\n{extracted_text}"

        try:
            # Attempt GPT-4o, fallback to GPT-3.5 if unavailable
            try:
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a precise instructional designer generating delivery-ready corporate training content."},
                        {"role": "user", "content": prompt}
                    ]
                )
            except Exception:
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a precise instructional designer generating delivery-ready corporate training content."},
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
            st.success("✅ All course materials generated successfully!")
            st.download_button("📥 Download All Materials (ZIP)", data=zip_buffer, file_name="Course_Materials.zip")
            st.download_button("Download Course Outline", open(outline_file, "rb"), file_name="Course_Outline.docx")
            st.download_button("Download Facilitator Guide", open(guide_file, "rb"), file_name="Facilitator_Guide.docx")
            st.download_button("Download Participant Workbook", open(workbook_file, "rb"), file_name="Participant_Workbook.docx")
            st.download_button("Download Quiz", open(quiz_file, "rb"), file_name="Quiz.docx")
            st.download_button("Download Slide Deck", slide_deck_file, file_name="Slide_Deck.pptx")

            # Show token usage
            try:
                tokens_used = completion.usage.total_tokens
                cost_estimate = round(tokens_used / 1000 * 0.03, 4)
                st.caption(f"Used {tokens_used} tokens · Estimated cost: ${cost_estimate:.4f}")
            except:
                pass

        except Exception as e:
            st.error(f"❌ Error generating content: {e}")
