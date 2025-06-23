import streamlit as st
import openai
import os
import tempfile
import zipfile
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page setup
st.set_page_config(page_title="AI Course Creator")
st.title("📚 AI Course Creator")

# Load OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY") or st.text_input("Enter your OpenAI API Key", type="password")
if not api_key:
    st.warning("Please enter your OpenAI API key to proceed.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# User inputs
st.header("Course Details")
topic = st.text_input("Course Topic")
audience = st.text_input("Target Audience")
duration = st.slider("Duration (minutes)", 30, 300, 90, step=15)
tonality = st.selectbox("Tone", ["Professional", "Conversational", "Inspirational", "Academic"])
notes = st.text_area("Optional: Add Notes (models, activity ideas, etc.)")

if st.button("Generate Course"):
    with st.spinner("Generating course content..."):
        prompt = f"""
        Create a {duration}-minute training course on "{topic}" for the audience "{audience}".
        Use a {tonality.lower()} tone. Include:

        1. Course Outline in a tabular format with columns: Time, Topic, Activity Type, Description
        2. Facilitator Guide with detailed session flow, definitions, transitions, case studies, discussion points
        3. Workbook with second-person instructions, exercises, and space for reflection
        4. Quiz with 3 MCQ, 2 MMCQ, and 2 True/False — with correct answers
        5. Slide Deck content: 1 slide per key idea, with bullets, quotes, and subpoints.

        {f"Use these notes:\n{notes}" if notes else ""}
        Return each section clearly labeled.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content

        # Split sections
        sections = {"Course_Outline": "", "Facilitator_Guide": "", "Workbook": "", "Quiz": "", "Slides": ""}
        current = None
        for line in content.splitlines():
            for key in sections:
                if key.replace("_", " ") in line:
                    current = key
            if current:
                sections[current] += line + "\n"

        def save_doc(text, filename):
            doc = Document()
            for line in text.strip().splitlines():
                doc.add_paragraph(line)
            path = os.path.join(tempfile.gettempdir(), filename)
            doc.save(path)
            return path

        # Slide creation
        def create_slide_deck(slide_text):
            prs = Presentation()
            for block in slide_text.strip().split("\n\n"):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                title, *bullets = block.strip().split("\n")
                slide.shapes.title.text = title.strip()
                content = slide.placeholders[1]
                for b in bullets:
                    content.text += b.strip() + "\n"
            slide_path = os.path.join(tempfile.gettempdir(), "Slide_Deck.pptx")
            prs.save(slide_path)
            return slide_path

        # Save all files
        outline_path = save_doc(sections["Course_Outline"], "Course_Outline.docx")
        guide_path = save_doc(sections["Facilitator_Guide"], "Facilitator_Guide.docx")
        workbook_path = save_doc(sections["Workbook"], "Participant_Workbook.docx")
        quiz_path = save_doc(sections["Quiz"], "Quiz.docx")
        slide_path = create_slide_deck(sections["Slides"])

        # Create ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.write(outline_path, "Course_Outline.docx")
            zipf.write(guide_path, "Facilitator_Guide.docx")
            zipf.write(workbook_path, "Participant_Workbook.docx")
            zipf.write(quiz_path, "Quiz.docx")
            zipf.write(slide_path, "Slide_Deck.pptx")
        zip_buffer.seek(0)

        st.success("✅ Course content generated!")
        st.download_button("📦 Download All as ZIP", zip_buffer, "Course_Materials.zip")
        st.download_button("📄 Course Outline", open(outline_path, "rb"), file_name="Course_Outline.docx")
        st.download_button("📄 Facilitator Guide", open(guide_path, "rb"), file_name="Facilitator_Guide.docx")
        st.download_button("📄 Participant Workbook", open(workbook_path, "rb"), file_name="Participant_Workbook.docx")
        st.download_button("📝 Quiz", open(quiz_path, "rb"), file_name="Quiz.docx")
        st.download_button("📽 Slide Deck", open(slide_path, "rb"), file_name="Slide_Deck.pptx")

        tokens = response.usage.total_tokens
        cost = round(tokens / 1000 * 0.01, 4)
        st.caption(f"Used {tokens} tokens · Estimated cost: ${cost}")
