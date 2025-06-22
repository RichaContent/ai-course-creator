import streamlit as st
import os
import openai
import tempfile
import fitz  # PyMuPDF for PDFs
import docx2txt
import mammoth  # For DOCX to text
from pptx import Presentation
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# Load OpenAI key from Streamlit Secrets or environment variable
openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="AI Training Course Creator")
st.title("🧠 AI Training Course Creator")
st.write("Create a ready-to-use training course with AI.")

# ---- Form ----
with st.form("course_form"):
    topic = st.text_input("📝 Course Topic")
    audience = st.text_input("🎯 Target Audience")
    duration = st.number_input("⏱️ Duration (in minutes)", min_value=10, max_value=480, step=10)
    tone = st.selectbox("✏️ Tone of Voice", ["Conversational", "Professional", "Inspiring", "Humorous"])
    level = st.selectbox("📚 Depth of Content", ["Beginner", "Intermediate", "Advanced"])

    uploaded_files = st.file_uploader("📤 Upload Reference Files (PDF, DOCX, PPTX)", accept_multiple_files=True, type=["pdf", "docx", "pptx"])
    design_notes = st.text_area("🧠 Add Your Design Notes", placeholder="E.g. Include examples, models to use, type of activities expected")
    feedback_notes = st.text_area("💬 Any feedback or changes for AI to consider? (optional)", placeholder="Add more interaction...")

    submitted = st.form_submit_button("🚀 Generate Course")

# ---- Helper Functions ----
def extract_text_from_file(uploaded_file):
    text = ""
    suffix = uploaded_file.name.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        if suffix == "pdf":
            reader = PdfReader(tmp_path)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif suffix == "docx":
            text = docx2txt.process(tmp_path)
        elif suffix == "pptx":
            prs = Presentation(tmp_path)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
    except Exception as e:
        text += f"\n[Error reading {uploaded_file.name}: {e}]"

    return text

def build_prompt():
    files_text = "\n".join([extract_text_from_file(file) for file in uploaded_files]) if uploaded_files else ""

    prompt = f"""
You are an instructional designer. Based on the topic "{topic}" for the audience "{audience}" and a duration of {duration} minutes, generate:

1. A detailed course outline (with session flow).
2. A facilitator guide with key talking points and suggested activities.
3. A quiz (5 questions) with answers.
4. Two workbook activities.

Tone: {tone}
Level: {level}

Incorporate these user notes if available:
{design_notes}

Reference content:
{files_text}

User feedback or changes to consider:
{feedback_notes}
"""
    return prompt

def save_to_doc(title, content):
    from docx import Document
    doc = Document()
    doc.add_heading(title, 0)
    for para in content.split("\n"):
        doc.add_paragraph(para)
    output_path = os.path.join(tempfile.gettempdir(), f"{title.replace(' ', '_')}.docx")
    doc.save(output_path)
    return output_path

# ---- Process and Generate ----
if submitted:
    if not topic or not audience or not duration:
        st.warning("Please fill in the required fields: topic, audience, duration.")
        st.stop()

    with st.spinner("Thinking hard... generating your course 🚧"):
        try:
            prompt = build_prompt()

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            content = response.choices[0].message.content if hasattr(response.choices[0], 'message') else response.choices[0].text

            if not content or len(content.strip()) < 20:
                st.error("AI did not return valid course content. Please try again with more input or better references.")
                st.stop()

            # Split content
            parts = content.split("\n\n")
            outline = next((p for p in parts if "outline" in p.lower()), "No outline found.")
            guide = next((p for p in parts if "facilitator" in p.lower()), "No facilitator guide found.")
            quiz = next((p for p in parts if "quiz" in p.lower()), "No quiz found.")
            activities = next((p for p in parts if "activity" in p.lower()), "No activities found.")

            files = {
                "Course_Outline.docx": save_to_doc("Course Outline", outline),
                "Facilitator_Guide.docx": save_to_doc("Facilitator Guide", guide),
                "Quiz.docx": save_to_doc("Quiz", quiz),
                "Workbook_Activities.docx": save_to_doc("Workbook Activities", activities)
            }

            st.success("✅ Your course has been generated!")
            for filename, path in files.items():
                with open(path, "rb") as f:
                    st.download_button(f"⬇️ Download {filename}", f, file_name=filename)

        except Exception as e:
            st.error(f"Something went wrong: {e}")
