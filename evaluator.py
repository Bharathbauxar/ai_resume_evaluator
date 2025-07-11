from PyPDF2 import PdfReader
import docx2txt

def extract_text_from_file(file_obj):
    filename = file_obj.name.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(file_obj)
        return " ".join(page.extract_text() or "" for page in reader.pages)

    elif filename.endswith(".docx"):
        with open("temp.docx", "wb") as f:
            f.write(file_obj.read())
        return docx2txt.process("temp.docx")

    elif filename.endswith(".txt"):
        return file_obj.read().decode("utf-8")

    return ""

def evaluate_resume(resume_text, required_skills):
    resume_text = resume_text.lower()
    resume_words = resume_text.split()

    matched = [skill for skill in required_skills if skill.lower() in resume_words]
    missing = [skill for skill in required_skills if skill.lower() not in resume_words]
    return matched, missing
