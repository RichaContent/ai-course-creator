import streamlit as st
import fitz  # PyMuPDF for PDF
import docx
from pptx import Presentation
import openai
import os

# ---------------- UI ----------------
st.set_page_config(page_title="AI Course Creator", layout="wide")
st.title("🎓 AI Course Creator")
st.write("Generate training courses using your notes or reference files (PDF, Word, PPT).")

# -------------- API Key --------------
openai_api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")
if not openai_api_key:
    st.warning("Please enter your API key to continue.")
    st.stop()

# -------------- User Inputs --------------
course_topic = st.text_input("📘 Course Topic")
audience = st.text_input("👥 Target Audience")
duration = st.number_input("⏱️ Duration in minutes", min_value=15, max_value=300, value=60)
tone = st.selectbox("🎯 Tone", ["Conversational", "Formal", "Inspirational"])
difficulty = st.selectbox("📚 Difficulty", ["Beginner", "Intermediate", "Advanced"])
user_notes = st.text_area("📝 Your Notes (models, examples, activities, etc.)")

# -------------- File Uploads --------------
uploaded_files = st.file_uploader("📂 Upload reference files (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"], accept_multiple_files=True)

# -------------- File Parsing Functions --------------
def extract_text_from_file(file):
    if file.name.endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file.name.endswith(".pptx"):
        prs = Presentation(file)
        slides_text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slides_text.append(shape.text)
        return "\n".join(slides_text)
    return ""

# -------------- Generate Button --------------
if st.button("🚀 Generate Course"):

    # Extract content from uploaded files
    reference_texts = []
    if uploaded_files:
        for file in uploaded_files:
            with st.spinner(f"Reading {file.name}..."):
                try:
                    ref = extract_text_from_file(file)
                    reference_texts.append(ref)
                except Exception as e:
                    st.error(f"Error reading {file.name}: {e}")
    
    combined_refs = "\n\n---\n\n".join(reference_texts)
    combined_refs = combined_refs[:2000]  # Limit to 2000 chars

    # Build prompt
    prompt = f"""
You are an expert instructional designer.

Generate a detailed training course on the topic: "{course_topic}".
Audience: {audience}
Duration: {duration} minutes
Tone: {tone}
Difficulty: {difficulty}

User Notes:
{user_notes}

Reference Material Extracted:
{combined_refs}
"""

    # -------------- Call OpenAI API --------------
    try:
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        course = response.choices[0].message.content
        token_used = response.usage.total_tokens
        cost_estimate = round(token_used * 0.00001, 4)

        st.success("✅ Course Generated!")
        st.markdown("### 📄 Course Output")
        st.markdown(course)

        st.info(f"Used {token_used} tokens · Estimated cost: ${cost_estimate}")

    except Exception as e:
        st.error(f"Error generating course: {e}")
