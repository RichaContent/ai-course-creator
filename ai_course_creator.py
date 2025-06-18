import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import os

# --- CONFIG ---
st.set_page_config(page_title="AI Course Creator", layout="wide")
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- HELPERS ---
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

# --- RESET SESSION ON FIRST LOAD ---
if "form_reset" not in st.session_state:
    st.session_state.form_reset = True
    st.session_state.topic = ""
    st.session_state.audience = ""
    st.session_state.tone = "Select"
    st.session_state.level = "Select"
    st.session_state.duration = 60

# --- UI HEADER ---
st.title("🧠 AI Training Course Creator")
st.markdown("Create a ready-to-use, structured training course using GPT-4o.")

# --- FORM ---
with st.form("course_form"):
    topic = st.text_input("📝 Course Topic", key="topic")
    audience = st.text_input("🎯 Audience", key="audience")
    duration = st.number_input("⏳ Duration (minutes)", 30, 480, value=st.session_state.duration, key="duration")
    tone = st.selectbox("🎤 Tone", ["Select", "Formal", "Conversational", "Inspiring"], key="tone")
    level = st.selectbox("📚 Difficulty Level", ["Select", "Beginner", "Intermediate", "Advanced"], key="level")
    submit = st.form_submit_button("🚀 Generate Course")

# --- SUBMIT ---
if submit:
    if not topic or not audience or tone == "Select" or level == "Select":
        st.error("⚠️ Please fill in all fields before generating the course.")
        st.stop()

    with st.spinner("Generating your training course..."):

        prompt = f"""
You are a world-class instructional designer. Create a {duration}-minute training course on "{topic}" for "{audience}". The tone should be {tone.lower()} and the difficulty level is {level.lower()}.

Include:
1. Course Outline with time blocks and method (activity, discussion, case study, etc.)
2. PowerPoint slide content: title and bullet points per slide
3. A 6-question quiz (MCQs) with correct answers marked
4. Workbook activities in second person (e.g. "Reflect on...", "Write down...", "Discuss...")
5. A detailed facilitator guide with instructions, tips, and timings

Label each section clearly.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        full_text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = estimate_cost(tokens)

    # --- PARSE RESPONSE ---
    sections = {
        "Course Outline": "",
        "Slides": [],
        "Quiz": "",
        "Workbook": "",
        "Facilitator Guide": ""
    }

    current = None
    for line in full_text.split("\n"):
        line = line.strip()
        if line.lower().startswith("1. course outline"):
            current = "Course Outline"
        elif line.lower().startswith("2. powerpoint"):
            current = "Slides"
        elif line.lower().startswith("3.") and "quiz" in line.lower():
            current = "Quiz"
        elif line.lower().startswith("4. workbook"):
            current = "Workbook"
        elif line.lower().startswith("5. facilitator"):
            current = "Facilitator Guide"
        elif current == "Slides" and line.lower().startswith("slide"):
            parts = line.split("–") if "–" in line else line.split("-")
            title = parts[0].strip() if parts else "Slide"
            content = parts[1].strip() if len(parts) > 1 else ""
            sections["Slides"].append({"title": title, "content": content})
        elif current:
            sections[current] += line + "\n"

    # --- SAVE FILES ---
    outline_path = save_doc(sections.get("Course Outline", "Not generated."), "Course_Outline.docx")
    slides_path = save_ppt(sections.get("Slides", []), "Slides.pptx")
    quiz_path = save_doc(sections.get("Quiz", "Not generated."), "Quiz.docx")
    workbook_path = save_doc(sections.get("Workbook", "Not generated."), "Workbook.docx")
    guide_path = save_doc(sections.get("Facilitator Guide", "Not generated."), "Facilitator_Guide.docx")

    # --- DISPLAY RESULTS ---
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

    # --- RESET FORM STATE AFTER SUCCESS ---
    st.session_state.clear()
    st.rerun()
