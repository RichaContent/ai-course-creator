import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import os

# Load API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Page config
st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🎓 AI Course Creator")
st.markdown("Generate structured training content with ease.")

# --- FORM INPUT ---
with st.form("course_form"):
    topic = st.text_input("📝 Course Topic", value="")
    audience = st.text_input("🎯 Audience", value="")
    duration = st.number_input("⏳ Duration (minutes)", 30, 480)
    tone = st.selectbox("🎤 Tone", ["Select", "Formal", "Conversational", "Inspiring"], index=0, key="tone_select")
    level = st.selectbox("📚 Difficulty Level", ["Select", "Beginner", "Intermediate", "Advanced"], index=0, key="level_select")
    submit = st.form_submit_button("🚀 Generate Course")

if submit:
    # Validation
    if not topic or not audience or tone == "Select" or level == "Select":
        st.error("Please fill in all fields.")
        st.stop()

    # Prompt
    prompt = f"""Create a {duration}-minute training course on "{topic}" for {audience}. 
Use a {tone.lower()} tone and {level.lower()} difficulty. Structure the output in these labeled sections:

1. Course Outline with Timings (include types of activities like discussion, case, video, roleplay, etc.)
2. Slide Content (bullets and titles for each section)
3. Quiz (5 MCQs with 4 options and correct answers)
4. Workbook Activities (in second person, with prompts, exercises, and space for answers; include 1 role play scenario)
5. Facilitator Guide (include instructions for facilitator, timings, engagement strategies)
"""

    # Show spinner
    with st.spinner("Generating content..."):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        result = response.choices[0].message.content
        usage = response.usage.total_tokens
        cost = round(usage / 100, 2)
        st.success("✅ Course created successfully!")

    # Token info
    st.caption(f"💬 Used {usage} tokens | Estimated cost: ${cost}")

    # --- FILE BUILDERS ---
    def save_doc(content, filename):
        doc = Document()
        for line in content.split('\n'):
            if line.strip().startswith(("-", "•", "*")):
                doc.add_paragraph(line.strip(), style='List Bullet')
            elif line.strip():
                doc.add_paragraph(line.strip())
        doc_path = os.path.join(os.getcwd(), filename)
        doc.save(doc_path)
        return doc_path

    def save_ppt(content, filename):
        prs = Presentation()
        for line in content.split('\n'):
            if line.strip().startswith("Slide"):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = line.strip()
            elif line.strip():
                try:
                    slide.placeholders[1].text += "\n" + line.strip()
                except:
                    continue
        ppt_path = os.path.join(os.getcwd(), filename)
        prs.save(ppt_path)
        return ppt_path

    # --- SPLIT CONTENT ---
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

    sections = extract_sections(result)

    # Save files
    outline_path = save_doc(sections.get("Outline", ""), "Course_Outline.docx")
    quiz_path = save_doc(sections.get("Quiz", ""), "Quiz.docx")
    workbook_path = save_doc(sections.get("Workbook", ""), "Workbook.docx")
    guide_path = save_doc(sections.get("Facilitator_Guide", ""), "Facilitator_Guide.docx")
    slides_path = save_ppt(sections.get("Slides", ""), "Slides.pptx")

    # Download buttons
    st.download_button("📥 Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
    st.download_button("📥 Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
    st.download_button("📥 Download Workbook", open(workbook_path, "rb"), file_name="Workbook.docx")
    st.download_button("📥 Download Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
    st.download_button("📥 Download Slides", open(slides_path, "rb"), file_name="Slides.pptx")

    # Clear session to remove prefill
    for key in st.session_state.keys():
        del st.session_state[key]
    st.experimental_rerun()
