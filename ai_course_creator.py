import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
import os

# Set page config
st.set_page_config(page_title="AI Course Creator", layout="wide")

# Use Streamlit secrets to access the API key securely
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Helper functions
def estimate_cost(tokens):
    return round(tokens / 1000 * 0.01, 4)  # $0.01 per 1K tokens (adjust for GPT-4 if needed)

def save_doc(content, filename):
    doc = Document()
    for line in content.split("\n"):
        doc.add_paragraph(line.strip())
    doc.save(filename)
    return filename

def save_ppt(slides, filename):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]

    for slide_data in slides:
        slide = prs.slides.add_slide(slide_layout)
        title = slide.shapes.title
        content = slide.placeholders[1]
        title.text = slide_data.get("title", "")
        content.text = slide_data.get("content", "")
    prs.save(filename)
    return filename

# App interface
st.title("🧠 AI Training Course Creator")
st.markdown("Create a ready-to-use training course with AI.")

with st.form("course_form"):
    topic = st.text_input("📝 Course Topic", value="Resilience")
    audience = st.text_input("🎯 Audience", value="First-time managers")
    duration = st.number_input("⏳ Duration (minutes)", min_value=30, max_value=480, value=90)
    tone = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"], index=1)
    level = st.selectbox("📚 Difficulty Level", ["Beginner", "Intermediate", "Advanced"], index=0)
    submit = st.form_submit_button("🚀 Generate Course")

if submit:
    with st.spinner("Creating your course..."):

        # Construct prompt
        system_prompt = f"""
You are a world-class instructional designer. Create a {duration}-minute training course on "{topic}" for "{audience}". The course should be {tone.lower()} in tone and suited to a {level.lower()} audience. 

Output the following sections:
1. Course Outline with timing and method of delivery per section (eg. discussion, activity, video, case, etc.)
2. PowerPoint slide content for each module (title + bullet points)
3. A 6-question quiz (MCQs) with correct answers marked
4. Workbook activities written for participants in 2nd person — include questions, space to write, or role-play prompts
5. A detailed facilitator guide with instructions to conduct each module effectively

Be clear and structured. Add visual suggestions for slides where useful.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7
        )

        result = response.choices[0].message.content
        total_tokens = response.usage.total_tokens
        cost = estimate_cost(total_tokens)

    # Split content into sections
    sections = {
        "Course Outline": "",
        "Slides": [],
        "Quiz": "",
        "Workbook": "",
        "Facilitator Guide": ""
    }

    current_section = None
    for line in result.split("\n"):
        line = line.strip()
        if line.lower().startswith("1. course outline"):
            current_section = "Course Outline"
        elif line.lower().startswith("2. powerpoint"):
            current_section = "Slides"
        elif line.lower().startswith("3. a 6-question"):
            current_section = "Quiz"
        elif line.lower().startswith("4. workbook"):
            current_section = "Workbook"
        elif line.lower().startswith("5. a detailed"):
            current_section = "Facilitator Guide"
        elif current_section == "Slides":
            if line.startswith("Slide"):
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
        elif current_section:
            sections[current_section] += line + "\n"

    # Save files
    outline_path = save_doc(sections["Course Outline"], "Course_Outline.docx")
    slides_path = save_ppt(sections["Slides"], "Slides.pptx")
    quiz_path = save_doc(sections["Quiz"], "Quiz.docx")
    workbook_path = save_doc(sections["Workbook"], "Workbook.docx")
    guide_path = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")

    # Show results
    st.success(f"Course generated using **{total_tokens} tokens**. Estimated cost: **${cost:.4f}**.")

    st.download_button("📥 Download Course Outline", data=open(outline_path, "rb"), file_name="Course_Outline.docx")
    st.download_button("📥 Download Slides (PPT)", data=open(slides_path, "rb"), file_name="Slides.pptx")
    st.download_button("📥 Download Quiz", data=open(quiz_path, "rb"), file_name="Quiz.docx")
    st.download_button("📥 Download Workbook", data=open(workbook_path, "rb"), file_name="Workbook.docx")
    st.download_button("📥 Download Facilitator Guide", data=open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
