import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

# App setup
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🧠 AI Training Course Creator")
st.markdown("Create a ready-to-use training course with AI.")

# Set OpenAI API key from Streamlit secrets
api_key = st.secrets["OPENAI_API_KEY"]
openai.api_key = api_key

# Input form
with st.form("course_form"):
    topic = st.text_input("📖 Course Topic")
    audience = st.text_input("🎯 Target Audience")
    duration = st.number_input("⏳ Duration (minutes)", min_value=30, max_value=480, step=10)
    tone = st.selectbox("🎤 Tone", ["Formal", "Conversational", "Inspiring"])
    level = st.selectbox("📚 Difficulty Level", ["Beginner", "Intermediate", "Advanced"])
    submitted = st.form_submit_button("🚀 Generate Course")

# Course generation
if submitted:
    if not topic or not audience or not tone or not level:
        st.error("⚠️ Please complete all fields.")
        st.stop()

    prompt = f"""
Create a {duration}-minute training course on "{topic}" for {audience}. 
Use a {tone.lower()} tone and {level.lower()} difficulty level.
Structure the output in 5 labeled sections:

1. **Course Outline** – show every module in order.  
   • Module title  
   • Exact hh:mm duration (adds up to total)  
   • Learning objective(s)  
   • Delivery method (lecture, case, discussion, activity, video, role-play)  
   • Brief content description

2. Slide Content – bullets with headings for each section
3. Quiz – 5 MCQs with 4 options each; indicate the correct one
4. Workbook Activities – written in second person, include writing space and one role-play scenario
5. Facilitator Guide – step-by-step instructions to deliver each part of the session
"""

    with st.spinner("Generating your course with GPT-4o..."):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.choices[0].message.content
            tokens = response.usage.total_tokens
            PRICE_PER_1K = 0.01
            cost = round(tokens / 1000 * PRICE_PER_1K, 4)
        except Exception as e:
            st.error(f"OpenAI Error: {str(e)}")
            st.stop()

    st.success("✅ Course generated!")
    st.caption(f"Used {tokens} tokens · Estimated cost: ${cost:.4f}")

    # Parse sections
    def extract_sections(text):
        sections = {}
        current = None
        for line in text.split("\n"):
            if line.strip().startswith("1. "): current = "Outline"
            elif line.strip().startswith("2. "): current = "Slides"
            elif line.strip().startswith("3. "): current = "Quiz"
            elif line.strip().startswith("4. "): current = "Workbook"
            elif line.strip().startswith("5. "): current = "Facilitator_Guide"
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
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        content_lines = content.split("\n")
        for i, line in enumerate(content_lines):
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

    def zip_bytes(paths_dict):
        buf = BytesIO()
        with ZipFile(buf, "w", ZIP_DEFLATED) as z:
            for name, path in paths_dict.items():
                z.write(path, arcname=name)
        buf.seek(0)
        return buf

    sections = extract_sections(result)

    outline_path = save_doc(sections.get("Outline", ""), "Course_Outline.docx")
    slides_path = save_ppt(sections.get("Slides", ""), "Slides.pptx")
    quiz_path = save_doc(sections.get("Quiz", ""), "Quiz.docx")
    workbook_path = save_doc(sections.get("Workbook", ""), "Workbook.docx")
    guide_path = save_doc(sections.get("Facilitator_Guide", ""), "Facilitator_Guide.docx")

    st.download_button("📥 Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx", mime="application/octet-stream")
    st.download_button("📥 Download Slides", open(slides_path, "rb"), file_name="Slides.pptx", mime="application/octet-stream")
    st.download_button("📥 Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx", mime="application/octet-stream")
    st.download_button("📥 Download Workbook", open(workbook_path, "rb"), file_name="Workbook.docx", mime="application/octet-stream")
    st.download_button("📥 Download Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx", mime="application/octet-stream")

    # ZIP Download
    zip_file = zip_bytes({
        "Course_Outline.docx": outline_path,
        "Slides.pptx":        slides_path,
        "Quiz.docx":          quiz_path,
        "Workbook.docx":      workbook_path,
        "Facilitator_Guide.docx": guide_path,
    })

    st.download_button("📦 Download ALL files (.zip)", data=zip_file, file_name="AI_Training_Course.zip", mime="application/zip")
