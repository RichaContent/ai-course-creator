import streamlit as st
import openai
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
import os
import re

# Functions
def save_doc(text, filename):
    doc = Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    path = os.path.join(os.getcwd(), filename)
    doc.save(path)
    return path

def save_ppt(text, filename):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]
    slides = text.split("\n\n")
    for s in slides:
        lines = s.split("\n")
        if len(lines) > 0:
            slide = prs.slides.add_slide(slide_layout)
            slide.shapes.title.text = lines[0][:50]
            slide.placeholders[1].text = "\n".join(lines[1:])
    path = os.path.join(os.getcwd(), filename)
    prs.save(path)
    return path

def extract_section(title, content):
    pattern = rf"{title}.*?(?=\n\d\.|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return match.group().strip() if match else f"{title} not found."

# Streamlit UI
st.set_page_config(layout="wide")
st.title("📘 AI Course Creator")

api_key = st.text_input("OpenAI API Key", type="password")
topic = st.text_input("Course Topic", placeholder="e.g., Resilience at Work")
audience = st.text_input("Target Audience", placeholder="e.g., Mid-level Managers")
duration = st.number_input("Duration (minutes)", min_value=30, max_value=300, value=60)
tone = st.selectbox("Tone", ["Professional", "Conversational", "Inspirational"])

if "output" not in st.session_state:
    st.session_state.output = {}

if st.button("Generate Course") and api_key and topic and audience:
    openai.api_key = api_key

    prompt = f"""You are a world-class instructional designer.
Create a {duration}-minute corporate training course on '{topic}' for {audience} in a {tone} tone.

Return your output in exactly the following 5 sections:

1. Course Outline  
- Break into modules with titles  
- Include learning objectives for each  
- Mention estimated time per module  
- Mention delivery method (e.g., discussion, video, role play, case study)

2. Facilitator Guide  
- Describe how to open the session  
- Give tips for facilitating each section  
- Include time markers  
- Provide debrief guidance after each activity

3. PowerPoint Slides  
- Slide title followed by 3-5 bullet points  
- Clear, instructional language

4. Workbook Activities  
- Write in second person (“You will…”)  
- Include instructions and space for writing  
- For role plays, describe the scenario and roles, not full scripts

5. Quiz  
- 5 multiple choice questions  
- Each with 4 options (A–D)  
- Clearly mark the correct answer (e.g., Correct answer: C)

Return the above 5 sections with clear headings."""

    with st.spinner("Generating course content..."):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
        tokens_used = getattr(response.usage, 'total_tokens', int(len(result.split()) * 1.33))
        st.session_state.output = {
            "outline": extract_section("1. Course Outline", result),
            "guide": extract_section("2. Facilitator Guide", result),
            "slides": extract_section("3. PowerPoint Slides", result),
            "activities": extract_section("4. Workbook Activities", result),
            "quiz": extract_section("5. Quiz", result),
            "tokens": tokens_used
        }

# Display & Downloads
if st.session_state.get("output"):
    out = st.session_state.output
    cost = round((out["tokens"] / 1000) * 0.01, 4)
    st.success(f"✅ Done! Used {out['tokens']} tokens. Estimated cost: ${cost}")

    outline_path = save_doc(out["outline"], "Course_Outline.docx")
    guide_path = save_doc(out["guide"], "Facilitator_Guide.docx")
    quiz_path = save_doc(out["quiz"], "Quiz.docx")
    activities_path = save_doc(out["activities"], "Workbook_Activities.docx")
    ppt_path = save_ppt(out["slides"], "Slides.pptx")

    st.download_button("📥 Download Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
    st.download_button("📥 Download Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
    st.download_button("📥 Download Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
    st.download_button("📥 Download Workbook Activities", open(activities_path, "rb"), file_name="Workbook_Activities.docx")
    st.download_button("📥 Download Slides", open(ppt_path, "rb"), file_name="Slides.pptx")
