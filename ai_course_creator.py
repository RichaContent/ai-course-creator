import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import os

# Set page config
st.set_page_config(page_title="AI Course Creator", layout="wide")

# Load OpenAI API key securely
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Cost estimator
def estimate_cost(tokens):
    return round(tokens / 1000 * 0.01, 4)

# Save .docx
def save_doc(content, filename):
    doc = Document()
    for line in content.split("\n"):
        if line.strip() != "":
            doc.add_paragraph(line.strip())
    doc.save(filename)
    return filename

# Save .pptx
def save_ppt(slides, filename):
    prs = Presentation()
    layout = prs.slide_layouts[1]
    for slide in slides:
        s = prs.slides.add_slide(layout)
        s.shapes.title.text = slide.get("title", "")
        s.placeholders[1].text = slide.get("content", "")
    prs.save(filename)
    return filename

# App UI
st.title("🧠 AI Training Course Creator")
st.markdown("Auto-generate training content using GPT-4o")

with st.form("course_form"):
    topic = st.text_input("📝 Course Topic", value="Resilience")
    audience = st.text_input("🎯 Audience", value="First-time managers")
    duration = st.number_input("⏳ Duration (minutes)", 30, 480, value=90)
    tone = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"], index=1)
    level = st.selectbox("📚 Difficulty Level", ["Beginner", "Intermediate", "Advanced"], index=0)
    submit = st.form_submit_button("🚀 Generate Course")

if submit:
    with st.spinner("Creating your course..."):

        # Prompt
        system_prompt = f"""
You are a world-class instructional designer. Create a {duration}-minute training course on "{topic}" for "{audience}". The tone should be {tone.lower()} and the audience level is {level.lower()}.

Generate the following:
1. Course Outline with timings and method of delivery (e.g., activity, case study, reflection)
2. PowerPoint slide content for each module (title + bullet points)
3. 6-question quiz in MCQ format, include correct answers
4. Workbook activities written in second person with space to write, questions, or role play prompts
5. Facilitator guide to help conduct the session effectively with instructions, timings, and facilitation tips

Be structured, concise, and helpful. Label each section clearly.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7
        )

        result = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = estimate_cost(tokens)

    # Parse response
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
        elif line.lower().startswith("3. 6-question"):
            current = "Quiz"
        elif line.lower().startswith("4. workbook"):
            current = "Workbook"
        elif line.lower().startswith("5. facilitator"):
            current = "Facilitator Guide"
        elif current == "Slides" and line.startswith("Slide"):
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

    # Save files
    outline_path = save_doc(sections["Course Outline"], "Course_Outline.docx")
    slides_path = save_ppt(sections["Slides"], "Slides.pptx")
    quiz_path = save_doc(sections["Quiz"], "Quiz.docx")
    workbook_path = save_doc(sections["Workbook"], "Workbook.docx")
    guide_path = save_doc(sections["Facilitator Guide"], "Facilitator_Guide.docx")

    # Display results
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
