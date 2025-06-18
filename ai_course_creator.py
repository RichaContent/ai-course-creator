import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import os

# Page config
st.set_page_config(page_title="AI Course Creator", layout="centered")

# Title
st.title("🎓 AI Course Creator")
st.markdown("This tool creates a complete training course with AI: Outline, Slides, Quiz, Workbook, Facilitator Guide.")

# Input fields
api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password", key="api_input")
topic = st.text_input("📘 Course Topic", key="topic_input")
audience = st.text_input("👥 Target Audience", key="audience_input")
duration = st.number_input("⏱ Duration (in minutes)", min_value=15, max_value=480, value=90, step=15, key="duration_input")
tone = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"], key="tone_input")
level = st.selectbox("🎚️ Complexity Level", ["Beginner", "Intermediate", "Advanced"], key="level_input")
generate_btn = st.button("🚀 Generate Course")

# Utility functions
def save_doc(content, filename):
    doc = Document()
    for part in content.split("\n\n"):
        doc.add_paragraph(part)
    filepath = os.path.join("/mount/src", filename)
    doc.save(filepath)
    return filepath

def save_ppt(slides, filename):
    prs = Presentation()
    for slide_text in slides.split("\n\n"):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title, *points = slide_text.strip().split("\n")
        slide.shapes.title.text = title.strip()
        content = slide.placeholders[1]
        content.text = "\n".join(p.strip("• ").strip() for p in points if p)
    filepath = os.path.join("/mount/src", filename)
    prs.save(filepath)
    return filepath

def zip_files(file_dict):
    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zipf:
        for name, path in file_dict.items():
            zipf.write(path, arcname=name)
    buf.seek(0)
    return buf

# Main logic
if generate_btn and all([api_key, topic, audience, duration]):
    openai.api_key = api_key

    st.info("⏳ Generating your course. Please wait...")

    prompt = f"""
You are an expert instructional designer. Design a complete {duration}-minute training course for the topic: "{topic}", for the audience: {audience}.

Use a {tone} tone and {level} complexity.

Return results in the following structured sections:

### Course_Outline
Show detailed flow:
- Module titles
- Exact timings (that total {duration} mins)
- Learning objectives
- Delivery method (lecture, case, activity, video, etc.)
- Description (1-2 lines)

### Slides
Provide slides content:
- Slide titles with 3-5 bullet points
- Match the outline sequence

### Quiz
5 MCQs:
- 4 answer options each
- One correct answer
- Clearly mark the correct one

### Workbook
Create activities in second person (you will...):
- Add reflection prompts
- Define role-play scenarios (not scripts)
- Use formatting for answer spaces

### Facilitator_Guide
A guide to deliver the session:
- Module-wise instructions
- Transitions, questions to ask
- Tips for leading discussions or role plays
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )

        output = response.choices[0].message.content
        tokens = response.usage.total_tokens
        price = round(tokens / 1000 * 0.01, 4)

        # Split into sections
        def extract_section(name):
            marker = f"### {name}"
            if marker in output:
                section = output.split(marker)[1].split("###")[0].strip()
                return section
            return ""

        sections = {
            "Course_Outline": extract_section("Course_Outline"),
            "Slides": extract_section("Slides"),
            "Quiz": extract_section("Quiz"),
            "Workbook": extract_section("Workbook"),
            "Facilitator_Guide": extract_section("Facilitator_Guide"),
        }

        st.success(f"✅ Course generated! Used {tokens} tokens · Estimated cost: ${price}")

        outline_path = save_doc(sections["Course_Outline"], "Course_Outline.docx")
        slides_path = save_ppt(sections["Slides"], "Slides.pptx")
        quiz_path = save_doc(sections["Quiz"], "Quiz.docx")
        workbook_path = save_doc(sections["Workbook"], "Workbook.docx")
        guide_path = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")

        # Download buttons
        st.download_button("📥 Download Course Outline", open(outline_path, "rb"), "Course_Outline.docx", mime="application/octet-stream")
        st.download_button("📥 Download Slides", open(slides_path, "rb"), "Slides.pptx", mime="application/octet-stream")
        st.download_button("📥 Download Quiz", open(quiz_path, "rb"), "Quiz.docx", mime="application/octet-stream")
        st.download_button("📥 Download Workbook", open(workbook_path, "rb"), "Workbook.docx", mime="application/octet-stream")
        st.download_button("📥 Download Facilitator Guide", open(guide_path, "rb"), "Facilitator_Guide.docx", mime="application/octet-stream")

        # ZIP All
        zip_buf = zip_files({
            "Course_Outline.docx": outline_path,
            "Slides.pptx": slides_path,
            "Quiz.docx": quiz_path,
            "Workbook.docx": workbook_path,
            "Facilitator_Guide.docx": guide_path,
        })

        st.download_button("📦 Download ALL as ZIP", data=zip_buf, file_name="AI_Course_Files.zip", mime="application/zip")

    except Exception as e:
        st.error(f"❌ Error: {e}")
