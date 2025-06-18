import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import os

# Page config
st.set_page_config(page_title="AI Course Creator", layout="wide")

# Secure API key from secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Helpers
def estimate_cost(tokens):
    return round(tokens / 1000 * 0.01, 4)

def save_doc(content, filename):
    doc = Document()
    for line in content.split("\n"):
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.save(filename)
    return filename

def save_ppt(slides, filename):
    prs = Presentation()
    layout = prs.slide_layouts[1]
    for slide in slides:
        s = prs.slides.add_slide(layout)
        s.shapes.title.text = slide.get("title", "")
        s.placeholders[1].text = slide.get("content", "")
    prs.save(filename)
    return filename

# UI
st.title("🧠 AI Training Course Creator")
st.markdown("Generate a structured training course in minutes using GPT-4o.")

with st.form("course_form"):
    topic = st.text_input("📝 Course Topic")
    audience = st.text_input("🎯 Audience")
    duration = st.number_input("⏳ Duration (minutes)", 30, 480)
    tone = st.selectbox("🎤 Tone", ["Select", "Formal", "Conversational", "Inspiring"])
    level = st.selectbox("📚 Difficulty Level", ["Select", "Beginner", "Intermediate", "Advanced"])
    submit = st.form_submit_button("🚀 Generate Course")

# Validate inputs
if submit:
    if not topic or not audience or tone == "Select" or level == "Select":
        st.error("⚠️ Please fill in all fields before generating the course.")
        st.stop()

    with st.spinner("Creating your course..."):

        # Prompt to GPT
        system_prompt = f"""
You are a world-class instructional designer. Create a {duration}-minute training course on "{topic}" for "{audience}". The tone should be {tone.lower()} and the audience level is {level.lower()}.

Generate the following:
1. Course Outline with timings and method of delivery (e.g., activity, case study, discussion)
2. PowerPoint slide content for each module (title + bullet points)
3. A 6-question quiz in MCQ format, with correct answers
4. Workbook activities written in second person with space to write, reflection questions, or role play prompts
5. A detailed facilitator guide with instructions, timings, and facilitation tips

Clearly label each section.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7
        )

        result = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = estimate_cost(tokens)

    # Parse GPT response
    sections = {
        "Course Outline": "",
        "Slides": [],
        "Quiz": "",
        "Workbook": "",
        "Facilitator Guide": ""
    }

    current = None
    for line in result.split("\n"):
        line = line.strip()
        if line.lower().startswith("1. course outline"):
            current = "Course Outline"
        elif line.lower().startswith("2. powerpoint"):
            current = "Slides"
        elif line.lower().startswith("3. a 6-question") or line.lower().startswith("3. quiz"):
            current = "Quiz"
        elif line.lower().startswith("4. workbook"):
            current = "Workbook"
        elif line.lower().startswith("5. facilitator"):
            current = "Facilitator Guide"
        elif current == "Slides" and line.lower().startswith("slide"):
            if "–" in line:
                parts = line.split("–")
            elif "-" in line:
                parts = line.split("-")
            else:
                parts = [line, ""]
            sections["Slides"].append({
                "title": parts[0].strip(),
                "content": parts[1].strip()
            })
        elif current:
            sections[current] += line + "\n"

    # Generate files with fallback if section is missing
    outline_path = save_doc(sections.get("Course Outline", "Outline not available."), "Course_Outline.docx")
    slides_path = save_ppt(sections.get("Slides", []), "Slides.pptx")
    quiz_path = save_doc(sections.get("Quiz", "Quiz not available."), "Quiz.docx")
    workbook_path = save_doc(sections.get("Workbook", "Workbook not available."), "Workbook.docx")
    guide_path = save_doc(sections.get("Facilitator Guide", "Facilitator guide not available."), "Facilitator_Guide.docx")

    # Display success + downloads
    st.success(f"✅ Generated using {tokens} tokens | Estimated cost: ${cost:.4f}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📄 Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
        st.download_button("📝 Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
    with col2:
        st.download_button("📚 Workbook", open(workbook_path, "rb"), file_name="Workbook.docx")
        st.download_button("👨‍🏫 Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
    with col3:
        st.download_button("📊 Slides (PPT)", open(slides_path, "rb"), file_name="Slides.pptx")
