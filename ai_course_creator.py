import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import os

# SETUP: Use environment variable or Streamlit secret
api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")
if not api_key:
    st.stop()
openai.api_key = api_key

# PAGE CONFIG
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🎓 AI Course Creator")

# FORM
with st.form("form"):
    topic = st.text_input("📝 Course Topic", value="")
    audience = st.text_input("🎯 Target Audience", value="")
    duration = st.number_input("⏳ Duration (minutes)", 30, 480)
    tone = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"], index=0)
    level = st.selectbox("📚 Difficulty Level", ["Beginner", "Intermediate", "Advanced"], index=0)
    submit = st.form_submit_button("🚀 Generate Course")

# HELPER FUNCTIONS
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
        if line.lower().startswith("slide"):
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = line.strip()
        elif line.strip():
            try:
                slide.placeholders[1].text += "\n" + line.strip()
            except:
                pass
    prs.save(filename)
    return filename

# ON SUBMIT
if submit:
    with st.spinner("Generating..."):
        prompt = f"""Create a {duration}-minute training course on "{topic}" for {audience}. 
Use a {tone.lower()} tone and {level.lower()} difficulty. Structure the output in these labeled sections:

1. Course Outline with Timings (include type of activity or delivery method)
2. Slide Content (bullet points and titles)
3. Quiz (5 MCQs with 4 options each + correct answers)
4. Workbook Activities (second person, space to write, role play scenarios)
5. Facilitator Guide (detailed instructions for each segment)
"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            st.error(f"OpenAI error: {e}")
            st.stop()

        output = response.choices[0].message.content
        usage = response.usage.total_tokens
        cost = round(usage / 100, 2)
        st.success("✅ Course created!")
        st.caption(f"Used {usage} tokens · Estimated cost: ${cost:.2f}")

        # PARSE SECTIONS
        sections = extract_sections(output)
        outline_path = save_doc(sections.get("Outline", ""), "Course_Outline.docx")
        slides_path = save_ppt(sections.get("Slides", ""), "Slides.pptx")
        quiz_path = save_doc(sections.get("Quiz", ""), "Quiz.docx")
        workbook_path = save_doc(sections.get("Workbook", ""), "Workbook.docx")
        facilitator_path = save_doc(sections.get("Facilitator", ""), "Facilitator_Guide.docx")

        # DOWNLOAD BUTTONS
        st.download_button("📥 Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
        st.download_button("📥 Download Slides", open(slides_path, "rb"), file_name="Slides.pptx")
        st.download_button("📥 Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
        st.download_button("📥 Download Workbook", open(workbook_path, "rb"), file_name="Workbook.docx")
        st.download_button("📥 Download Facilitator Guide", open(facilitator_path, "rb"), file_name="Facilitator_Guide.docx")
