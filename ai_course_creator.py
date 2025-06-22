import streamlit as st
import os
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import base64
import fitz  # PyMuPDF
import tempfile
import zipfile

# Load OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# App title
st.set_page_config(page_title="AI Course Creator", layout="wide")
st.title("🧠 AI Course Creator")
st.markdown("Like Canva, but for corporate trainers. Create structured courses in minutes!")

# Helper: Save Word file
def save_word(content_list, filename):
    doc = Document()
    for para in content_list:
        doc.add_paragraph(para)
    path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(path)
    return path

# Helper: Create a PPT slide deck
def save_ppt(slides, filename):
    prs = Presentation()
    for title, content in slides:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = title
        slide.placeholders[1].text = content
    path = os.path.join(tempfile.gettempdir(), filename)
    prs.save(path)
    return path

# Helper: Extract text from uploaded file
def extract_text(uploaded_file):
    if uploaded_file.type == "application/pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            doc = fitz.open(tmp.name)
            text = "\n".join(page.get_text() for page in doc)
            return text
    elif uploaded_file.type.startswith("application/vnd.openxmlformats"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode()
    return ""

# Form
with st.form("course_form"):
    topic = st.text_input("Course Topic")
    audience = st.text_input("Target Audience")
    duration = st.text_input("Course Duration (minutes or hours)")
    objectives = st.text_area("Learning Objectives (bullet points)", placeholder="- Learn resilience\n- Apply frameworks")
    tone = st.selectbox("Preferred Tone", ["Formal", "Conversational", "Inspiring"], index=0)
    depth = st.selectbox("Depth of Content", ["Beginner", "Intermediate", "Advanced"], index=0)

    # Optional Notes
    user_notes = st.text_area("Notes to AI (optional)", placeholder="Include role plays, case studies, Kolb’s model...")

    # Optional upload
    uploaded_file = st.file_uploader("Upload SME Document (optional)", type=["pdf", "docx", "pptx", "txt"])

    # Optional feedback
    feedback = st.text_area("Any feedback or changes for AI to consider? (optional)", placeholder="Add more interaction...")

    submitted = st.form_submit_button("Generate Course")

if submitted:
    with st.spinner("Creating your course..."):
        # Build prompt
        prompt = f"""
Create a {duration} training course on "{topic}" for {audience}.
Learning objectives:
{objectives}

Tone: {tone}
Depth: {depth}
"""
        if user_notes:
            prompt += f"\nUser notes:\n{user_notes}"
        if feedback:
            prompt += f"\nRevise using this feedback:\n{feedback}"
        if uploaded_file:
            extracted = extract_text(uploaded_file)
            prompt += f"\nReference content:\n{extracted[:2000]}..."

        # Call OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        full_text = response.choices[0].message.content.strip()

        # Split output
        def split_sections(text):
            sections = {"Course_Outline": [], "Quiz": [], "Workbook": [], "Facilitator_Guide": []}
            current = None
            for line in text.splitlines():
                if "course outline" in line.lower():
                    current = "Course_Outline"
                elif "quiz" in line.lower():
                    current = "Quiz"
                elif "workbook" in line.lower():
                    current = "Workbook"
                elif "facilitator guide" in line.lower():
                    current = "Facilitator_Guide"
                elif current:
                    sections[current].append(line)
            return sections

        sections = split_sections(full_text)

        # Save files
        outline_path = save_word(sections["Course_Outline"], "Course_Outline.docx")
        quiz_path = save_word(sections["Quiz"], "Quiz.docx")
        workbook_path = save_word(sections["Workbook"], "Workbook.docx")
        guide_path = save_word(sections["Facilitator_Guide"], "Facilitator_Guide.docx")

        slides = [("Slide 1", "Course Overview"), ("Slide 2", topic)]
        ppt_path = save_ppt(slides, "Slides.pptx")

        # Zip all
        zip_file = os.path.join(tempfile.gettempdir(), "Course_Package.zip")
        with zipfile.ZipFile(zip_file, "w") as zf:
            for file in [outline_path, quiz_path, workbook_path, guide_path, ppt_path]:
                zf.write(file, os.path.basename(file))

        # Download links
        st.success("✅ Course Created!")
        st.download_button("📥 Download All Files (ZIP)", data=open(zip_file, "rb").read(), file_name="Course_Package.zip")

        st.download_button("📘 Course Outline", open(outline_path, "rb").read(), file_name="Course_Outline.docx")
        st.download_button("❓ Quiz", open(quiz_path, "rb").read(), file_name="Quiz.docx")
        st.download_button("🧩 Workbook", open(workbook_path, "rb").read(), file_name="Workbook.docx")
        st.download_button("🎓 Facilitator Guide", open(guide_path, "rb").read(), file_name="Facilitator_Guide.docx")
        st.download_button("📊 Slide Deck", open(ppt_path, "rb").read(), file_name="Slides.pptx")

        # Token Estimate
        total_tokens = len(prompt.split()) + len(full_text.split())
        token_cost = round(total_tokens * 0.01, 2)
        st.info(f"Used approx. {total_tokens} tokens · Estimated cost: ${token_cost}")
