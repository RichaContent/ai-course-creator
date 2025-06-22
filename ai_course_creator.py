import os
import tempfile
import zipfile
from typing import List

import openai
import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
from pptx import Presentation

# Use the secret key from Streamlit Cloud if available
openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else None

st.set_page_config(page_title="AI Training Course Creator", layout="wide")
st.title("🧠 AI Training Course Creator")
st.caption("Create a ready-to-use training course with AI.")

# Optional: manually input API key if not set in secrets
if not openai.api_key:
    openai.api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")
    if not openai.api_key:
        st.info("Please enter your OpenAI API key to proceed.")
        st.stop()

# Input fields
topic = st.text_input("📝 Course Topic", "")
audience = st.text_input("🎯 Target Audience", "")
duration = st.number_input("⏰ Duration (in minutes)", min_value=30, max_value=480, step=15)
tone = st.selectbox("🖋️ Tone of Voice", ["Professional", "Conversational", "Inspiring", "Authoritative"])
depth = st.selectbox("📚 Depth of Content", ["Beginner", "Intermediate", "Advanced"])

uploaded_files = st.file_uploader("📎 Upload Reference Files (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)
user_notes = st.text_area("💡 Add Your Design Notes", placeholder="Any models to include, activities you want, case studies etc. (optional)")
feedback = st.text_area("🗣️ Any feedback or changes for AI to consider? (optional)", placeholder="Add more interaction...")

if st.button("🚀 Generate Course"):
    with st.spinner("Creating your course materials..."):
        # Process uploaded files
        reference_texts = []
        for file in uploaded_files:
            if file.name.endswith(".pdf"):
                reader = PdfReader(file)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
                reference_texts.append(text)
            elif file.name.endswith(".docx"):
                doc = Document(file)
                text = "\n".join([para.text for para in doc.paragraphs])
                reference_texts.append(text)
            elif file.name.endswith(".pptx"):
                prs = Presentation(file)
                text = "\n".join(
                    [shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")]
                )
                reference_texts.append(text)

        # Combine inputs for prompt
        prompt_parts = [
            f"Design a training course for corporate learners.",
            f"Topic: {topic}" if topic else "",
            f"Target Audience: {audience}" if audience else "",
            f"Duration: {duration} minutes" if duration else "",
            f"Tone of Voice: {tone}",
            f"Depth of Content: {depth}",
            f"User Notes: {user_notes}" if user_notes else "",
            f"Feedback to consider: {feedback}" if feedback else "",
            "Here are some reference materials:\n" + "\n\n".join(reference_texts) if reference_texts else "",
            "Please generate the following structured outputs:\n"
            "1. Course Outline\n2. Facilitator Guide\n3. Quiz with answers\n4. Activities with instructions"
        ]
        prompt = "\n".join([p for p in prompt_parts if p])

        # OpenAI Call
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
        except Exception as e:
            st.error(f"OpenAI Error: {e}")
            st.stop()

        content = response.choices[0].message.content

        # Split generated content
        sections = {
            "Course_Outline": "",
            "Facilitator_Guide": "",
            "Quiz": "",
            "Activities": ""
        }
        current_section = None
        for line in content.split("\n"):
            line_lower = line.lower().strip()
            if "course outline" in line_lower:
                current_section = "Course_Outline"
            elif "facilitator guide" in line_lower:
                current_section = "Facilitator_Guide"
            elif "quiz" in line_lower:
                current_section = "Quiz"
            elif "activities" in line_lower:
                current_section = "Activities"
            elif current_section:
                sections[current_section] += line + "\n"

        # Save to files
        def save_doc(text, filename):
            doc = Document()
            doc.add_heading(filename.replace("_", " ").replace(".docx", ""), level=1)
            for para in text.strip().split("\n"):
                doc.add_paragraph(para)
            path = os.path.join(tempfile.gettempdir(), filename)
            doc.save(path)
            return path

        files = []
        for name, content in sections.items():
            filepath = save_doc(content, f"{name}.docx")
            files.append(filepath)

        # ZIP all files
        zip_path = os.path.join(tempfile.gettempdir(), "Course_Materials.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for f in files:
                zipf.write(f, os.path.basename(f))

        # File Downloads
        for f in files:
            with open(f, "rb") as file:
                st.download_button(f"📥 Download {os.path.basename(f)}", file.read(), file_name=os.path.basename(f))

        with open(zip_path, "rb") as zipf:
            st.download_button("📦 Download All as ZIP", zipf.read(), file_name="Course_Materials.zip")

        st.success("✅ Course generated successfully!")
