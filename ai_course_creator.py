import streamlit as st
import os
import tempfile
import docx
import openai
import fitz  # PyMuPDF for PDF
from pptx import Presentation
from docx import Document

# Initialize OpenAI client
client = openai.OpenAI()

st.set_page_config(page_title="AI Course Creator", layout="centered")
st.title("🧠 AI Training Course Creator")
st.write("Create a ready-to-use training course with AI.")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.warning("OpenAI API key not found in environment. Please set it in Streamlit secrets.")
    st.stop()

# Collect inputs from the user
topic = st.text_input("🗋 Course Topic")
audience = st.text_input("🍒 Target Audience")
duration = st.number_input("⏱️ Duration (in minutes)", min_value=15, max_value=480, step=15)
tone = st.selectbox("🎮 Tone of Voice", ["Professional", "Conversational", "Inspiring", "Authoritative"])
depth = st.selectbox("🎓 Depth of Content", ["Beginner", "Intermediate", "Advanced"])

st.markdown("**📂 Upload Reference Files (PDF, DOCX, PPTX)**")
uploaded_files = st.file_uploader("Drag and drop files here", type=["pdf", "docx", "pptx"], accept_multiple_files=True)

design_notes = st.text_area("**🧠 Add Your Design Notes**", help="Add any specific instructions or references for the AI (optional)")
review_feedback = st.text_area("**Any feedback or changes for AI to consider? (optional)**")

if st.button("🚀 Generate Course"):
    if not topic or not audience:
        st.error("Please fill in at least the course topic and audience.")
        st.stop()

    with st.spinner("Generating your course materials..."):

        def extract_text(file):
            ext = file.name.split(".")[-1].lower()
            text = ""
            if ext == "pdf":
                doc = fitz.open(stream=file.read(), filetype="pdf")
                for page in doc:
                    text += page.get_text()
            elif ext == "docx":
                doc = Document(file)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif ext == "pptx":
                prs = Presentation(file)
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text += shape.text + "\n"
            return text.strip()

        # Compile uploaded content
        reference_texts = []
        for file in uploaded_files:
            try:
                ref_text = extract_text(file)
                reference_texts.append(ref_text)
            except Exception as e:
                reference_texts.append(f"Error reading {file.name}: {str(e)}")

        # Compose prompt
        prompt = f"""
You are a professional instructional designer. Create a course on the topic "{topic}" for the audience "{audience}".
Duration of the course should be around {duration} minutes.
The tone of voice should be {tone}, and the depth of content should be {depth}.
Use the following references and user notes:
{design_notes}
{review_feedback}
"""
        if reference_texts:
            prompt += "\n\nREFERENCE CONTENT:\n" + "\n\n".join(reference_texts)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            full_text = response.choices[0].message.content.strip()

            def save_doc(text, filename):
                doc_path = os.path.join(tempfile.gettempdir(), filename)
                doc = Document()
                for para in text.split("\n"):
                    doc.add_paragraph(para)
                doc.save(doc_path)
                return doc_path

            # Split content
            sections = {
                "Course_Outline": "Course Outline",
                "Facilitator_Guide": "Facilitator Guide",
                "Participant_Handout": "Participant Handout"
            }
            generated_files = []
            for key, section in sections.items():
                if section.lower() in full_text.lower():
                    part = full_text.split(section)[-1].strip().split("\n\n")[0:5]
                    doc_path = save_doc("\n\n".join(part), f"{key}.docx")
                    generated_files.append(doc_path)

            for path in generated_files:
                st.download_button(
                    label=f"📄 Download {os.path.basename(path)}",
                    data=open(path, "rb").read(),
                    file_name=os.path.basename(path),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
