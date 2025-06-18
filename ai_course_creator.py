import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import os

# UI Config
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🧠 AI Training Course Creator")
st.markdown("Create a ready-to-use training course with AI.")

# Step 1: Enter API Key
api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")
if not api_key:
    st.info("Please enter your OpenAI API key to proceed.")
    st.stop()
openai.api_key = api_key

# Step 2: User Inputs (Empty Fields)
with st.form("course_form"):
    topic = st.text_input("📖 Course Topic", value="")
    audience = st.text_input("🎯 Target Audience", value="")
    duration = st.number_input("⏳ Duration (minutes)", min_value=30, max_value=480, step=10)
    tone = st.selectbox("🎤 Tone", ["Select", "Formal", "Conversational", "Inspiring"])
    level = st.selectbox("📚 Difficulty Level", ["Select", "Beginner", "Intermediate", "Advanced"])
    submitted = st.form_submit_button("🚀 Generate Course")

# Step 3: Generate AI Output
if submitted:
    if not topic or not audience or tone == "Select" or level == "Select":
        st.error("⚠️ Please fill in all fields.")
        st.stop()

    prompt = f"""
Create a {duration}-minute training course on "{topic}" for {audience}. 
Use a {tone.lower()} tone and {level.lower()} difficulty level.
Structure the output in these 5 labeled sections:

1. Course Outline with Timings (mention the type of activity: discussion, case, roleplay, video, etc.)
2. Slide Content (bullets with headings for each section)
3. Quiz (5 MCQs with 4 options each, mark the correct answer)
4. Workbook Activities (written in second person, include prompts, space to respond, and one role play scenario)
5. Facilitator Guide (step-by-step instruction for the facilitator)
"""

    with st.spinner("Generating your course with GPT-4o..."):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.choices[0].message.content
            tokens = response.usage.total_tokens
            cost = round(tokens / 100, 2)
        except Exception as e:
            st.error(f"OpenAI Error: {str(e)}")
            st.stop()

    st.success("✅ Course generated successfully!")
    st.caption(f"Used {tokens} tokens · Estimated cost: ${cost:.2f}")

    # Step 4: Parse sections
    def extract_sections(text):
        sections = {}
        current = None
        for line in text.split("\n"):
            if line.strip().startswith("1. "): current = "Outline"
            elif line.strip().startswith("2. "): current = "Slides"
            elif line.strip().startswith("3. "): current = "Quiz"
            elif line.strip().startswith("4. "): current = "Workbook"
            elif line.strip().startswith("5. "): current = "Facilitator"
            if current:
                sections.setdefault(current, "")
                sections[current] += line + "\n"
        return sections

    def save_doc(content, filename):
        doc = Document()
        for line in content.split('\n'):
            if line.strip().startswith(("-", "*", "•")):
                doc.add_paragraph(line.strip(), style='List Bullet')
            elif line.strip():
                doc.add_paragraph(line.strip())
        doc.save(filename)
        return filename

    def save_ppt(content, filename):
        prs = Presentation()
        for line in content.split("\n"):
            if line.strip().lower().startswith("slide"):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = line.strip()
            elif line.strip():
                try:
                    slide.placeholders[1].text += "\n" + line.strip()
                except:
                    pass
        prs.save(filename)
        return filename

    # Step 5: Save & Download files
    sections = extract_sections(result)

    outline_path = save_doc(sections.get("Outline", ""), "Course_Outline.docx")
    slides_path = save_ppt(sections.get("Slides", ""), "Slides.pptx")
    quiz_path = save_doc(sections.get("Quiz", ""), "Quiz.docx")
    workbook_path = save_doc(sections.get("Workbook", ""), "Workbook.docx")
    facilitator_path = save_doc(sections.get("Facilitator", ""), "Facilitator_Guide.docx")

    st.download_button("📥 Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
    st.download_button("📥 Download Slides", open(slides_path, "rb"), file_name="Slides.pptx")
    st.download_button("📥 Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
    st.download_button("📥 Download Workbook", open(workbook_path, "rb"), file_name="Workbook.docx")
    st.download_button("📥 Download Facilitator Guide", open(facilitator_path, "rb"), file_name="Facilitator_Guide.docx")
