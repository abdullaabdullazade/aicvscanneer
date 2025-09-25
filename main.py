from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PyPDF2 import PdfReader
from dotenv import load_dotenv

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["ALLOWED_EXTENSIONS"] = {"txt", "pdf"}

load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not found in environment variables")
genai.configure(api_key=API_KEY)


LANGUAGES = [
    "English",
    "Azerbaijani",
    "Turkish",
    "Russian",
    "French",
    "Spanish",
    "German",
]


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def analyze_cv_with_gemini(text, language):
    print(language)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    Analyze this CV text and give answer at {language}. Extract and detail the following:
    - Full name of the candidate
    - Education background
    - Work experience (list jobs with dates and descriptions)
    - Skills
    - Suitable job positions based on the CV
    - Any other relevant details like contact info, certifications, etc.
    
    Provide a detailed summary.
    
    CV Text:
    {text}


    """
    response = model.generate_content(prompt)
    return response.text


@app.route("/")
def index():
    return render_template("index.html", languages=LANGUAGES)


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"})

    file = request.files["file"]
    language = request.form.get("language")

    if not language or language not in LANGUAGES:
        return jsonify({"error": "Invalid language selected"})

    if file.filename == "":
        return jsonify({"error": "No selected file"})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif filename.endswith(".txt"):
            text = extract_text_from_txt(file_path)
        else:
            os.remove(file_path)
            return jsonify({"error": "Invalid file type"})

        try:
            analysis = analyze_cv_with_gemini(text, language)
            os.remove(file_path)
            return jsonify({"analysis": analysis})
        except Exception as e:
            os.remove(file_path)
            return jsonify({"error": str(e)})

    return jsonify({"error": "File not allowed"})


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True)
