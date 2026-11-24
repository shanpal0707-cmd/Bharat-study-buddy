
import os
import json
import sqlite3
import re
import time
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from functools import wraps

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from google import genai

from video_processor import transcribe_video
from pdf_processor import extract_pdf_text
from ppt_processor import extract_ppt_text
from knowledge_base import save_knowledge_base, search_knowledge
from database import init_database, get_connection


# =========================================================
# CONFIGURATION
# =========================================================

ROOT_FOLDER = os.path.dirname(os.path.dirname(__file__))

load_dotenv(os.path.join(ROOT_FOLDER, ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # Local development only

CORS(
    app,
    supports_credentials=True,
    origins=["http://127.0.0.1:5500",
             "http://127.0.0.1:5501",
        "http://localhost:5500",
        "http://localhost:5501",
        ]
)

# Guru AI Voice Assistant Blueprint
from guru_routes import guru_bp
app.register_blueprint(guru_bp)

# Paper Analyzer AI Blueprint
from paper_analyzer_routes import paper_analyzer_bp
app.register_blueprint(paper_analyzer_bp)

UPLOAD_FOLDER = os.path.join(ROOT_FOLDER, "data", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# AUTHENTICATION HELPER
# =========================================================

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "success": False,
                "message": "Please log in to continue."
            }), 401

        return function(*args, **kwargs)

    return wrapper


def get_logged_in_user_id():
    return session.get("user_id")


def get_user_upload_folder(user_id):
    folder = os.path.join(UPLOAD_FOLDER, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def save_uploaded_file(file, user_id):
    safe_name = secure_filename(file.filename)

    if not safe_name:
        raise ValueError("Invalid filename.")

    # Keep each user's uploads separate and avoid filename collisions.
    import uuid
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    folder = get_user_upload_folder(user_id)
    file_path = os.path.join(folder, unique_name)

    file.save(file_path)
    return file_path


def clean_json_response(raw_text):
    raw_text = raw_text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "", 1)
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "Bharat Study Buddy backend is running"
    })


# =========================================================
# PDF UPLOAD
# =========================================================

@app.route("/api/upload/pdf", methods=["POST"])
@login_required
def upload_pdf():
    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "No PDF file received."
            }), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({
                "success": False,
                "message": "No file selected."
            }), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({
                "success": False,
                "message": "Only PDF files are allowed."
            }), 400

        user_id = get_logged_in_user_id()
        file_path = save_uploaded_file(file, user_id)

        pages = extract_pdf_text(file_path)

        save_knowledge_base(
            pdf_data=pages,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "message": "PDF processed successfully.",
            "filename": file.filename,
            "total_pages": len(pages),
            "pages": pages
        })

    except Exception as error:
        print("PDF UPLOAD ERROR:", error)
        return jsonify({
            "success": False,
            "message": "PDF processing failed. Please check the file and try again."
        }), 500


# =========================================================
# PPT UPLOAD
# =========================================================

@app.route("/api/upload/ppt", methods=["POST"])
@login_required
def upload_ppt():
    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "No PPT file received."
            }), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({
                "success": False,
                "message": "No file selected."
            }), 400

        if not file.filename.lower().endswith((".ppt", ".pptx")):
            return jsonify({
                "success": False,
                "message": "Only PPT/PPTX files are allowed."
            }), 400

        user_id = get_logged_in_user_id()
        file_path = save_uploaded_file(file, user_id)

        slides = extract_ppt_text(file_path)

        save_knowledge_base(
            ppt_data=slides,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "message": "PowerPoint processed successfully.",
            "filename": file.filename,
            "total_slides": len(slides),
            "slides": slides
        })

    except Exception as error:
        print("PPT UPLOAD ERROR:", error)
        return jsonify({
            "success": False,
            "message": "PowerPoint processing failed. Please check the file and try again."
        }), 500


# =========================================================
# VIDEO UPLOAD
# =========================================================

@app.route("/api/upload/video", methods=["POST"])
@login_required
def upload_video():
    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "No video file received."
            }), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({
                "success": False,
                "message": "No file selected."
            }), 400

        allowed_extensions = (
            ".mp4", ".mov", ".avi", ".mkv", ".webm"
        )

        if not file.filename.lower().endswith(allowed_extensions):
            return jsonify({
                "success": False,
                "message": "Unsupported video format."
            }), 400

        user_id = get_logged_in_user_id()
        file_path = save_uploaded_file(file, user_id)

        transcript = transcribe_video(file_path)

        save_knowledge_base(
            video_data=transcript,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "message": "Video processed successfully.",
            "filename": file.filename,
            "segments": len(transcript),
            "transcript": transcript
        })

    except Exception as error:
        print("VIDEO UPLOAD ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Video processing failed. Please check the file and try again."
        }), 500


# =========================================================
# ASK AI
# =========================================================

@app.route("/api/ask", methods=["POST"])
@login_required
def ask_ai():
    try:
        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()

        if not question:
            return jsonify({
                "success": False,
                "message": "Question is required."
            }), 400

        user_id = get_logged_in_user_id()

        sources = search_knowledge(
            question,
            top_k=5,
            user_id=user_id
        )

        if not sources:
            return jsonify({
                "success": True,
                "answer": "I couldn't find this information in your uploaded study materials.",
                "sources": []
            })

        context_parts = []

        for source in sources:
            citation = source["source"]

            if source["source"] == "PDF":
                citation += f" Page {source.get('page')}"

            elif source["source"] == "PPT":
                citation += f" Slide {source.get('slide')}"

            elif source["source"] == "VIDEO":
                citation += (
                    f" {source.get('start')}s - "
                    f"{source.get('end')}s"
                )

            context_parts.append(
                f"[{citation}]\n{source['text']}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""
You are Bharat Study Buddy, an AI tutor.

Answer ONLY using the study material provided below.
Do not use outside knowledge or invent facts.
If the answer is unsupported, say:
"I couldn't find this information in your uploaded study materials."
Explain simply and cite relevant sources.

STUDY MATERIAL:
{context}

STUDENT QUESTION:

{question}
"""

        response = client.responses.create(
            model=GROQ_MODEL,
            input=prompt
        )

        return jsonify({
            "success": True,
            "answer": response.output_text,
            "sources": sources
        })

    except Exception as error:
        print("ASK AI ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Unable to answer right now. Please try again."
        }), 500


# =========================================================
# AI DIAGRAM EXPLAINER
# =========================================================

DIAGRAM_SYSTEM_PROMPT = """You are Bharat Study Buddy's expert AI Diagram Explainer, an AI tutor designed for Indian and international college students.
A student has uploaded an educational diagram or chart and asked for an explanation.

Your task is to analyze the image with high technical and educational precision:
1. OVERVIEW: Identify what subject or concept this diagram illustrates (e.g. Operating Systems [Process States, Paging, Deadlocks], Computer Networks [OSI model, TCP/IP, Handshake, Routing], DBMS [ER Diagrams, Normalization, ACID transactions], Data Structures [Trees, Graphs, Queues], Computer Architecture [Pipelines, Memory Hierarchy], Biology, Physics, or other disciplines).
2. KEY COMPONENTS & LABELS: Detect every visible label, box, block, state, table, node, or component. Clearly explain the role and function of each component.
3. STEP-BY-STEP PROCESS / FLOW: Trace directional arrows, sequence numbers, data paths, control flows, or state transitions in exact order. Explain step-by-step how the system transitions from one state/step to the next.
4. COMPONENT RELATIONSHIPS: Explain how different parts depend on or communicate with each other.
5. ADDRESS THE STUDENT'S QUESTION: If the student asked a specific question or follow-up, answer it directly using evidence from the diagram. If the question was generic or empty, provide a comprehensive walkthrough.
6. HONESTY & ACCURACY: If any part, label, or text in the diagram is cut off, blurry, or unreadable, explicitly mention: "Note: Some labels/portions of this diagram are unclear, so..." instead of making up or hallucinating components.
7. FORMATTING: Present your explanation in student-friendly Markdown with bold headings, clean bullet points, numbered steps, and key takeaways for exams.
"""

ALLOWED_DIAGRAM_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_DIAGRAM_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def generate_diagram_explanation(image, question):
    if not gemini_client:
        raise RuntimeError("GEMINI_API_KEY is not configured on the server.")

    user_query = question.strip() if question and question.strip() else "Please explain this diagram step by step, identify its components, and explain how it works."

    candidate_models = ["gemini-3-flash-preview", "gemini-flash-lite-latest", "gemini-3.5-flash-lite", GEMINI_MODEL]
    seen = set()
    models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

    last_error = None
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=[
                        image,
                        DIAGRAM_SYSTEM_PROMPT,
                        f"Student Question: {user_query}"
                    ]
                )
                if response and response.text:
                    return response.text
            except Exception as err:
                last_error = err
                err_str = str(err).upper()
                if "503" in err_str or "UNAVAILABLE" in err_str or "DEMAND" in err_str:
                    time.sleep(1)
                    continue
                else:
                    break

    if last_error:
        raise last_error
    raise RuntimeError("Failed to generate diagram explanation. Please try again.")


@app.route("/api/ask/diagram", methods=["POST"])
@login_required
def ask_ai_diagram():
    try:
        user_id = get_logged_in_user_id()
        question = request.form.get("question", "").strip()
        image_file = request.files.get("image")

        active_file_path = None
        diagram_filename = None

        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1].lower()
            if ext not in ALLOWED_DIAGRAM_EXTENSIONS:
                return jsonify({
                    "success": False,
                    "message": f"Unsupported file type ({ext}). Please upload PNG, JPG, JPEG, or WEBP."
                }), 400

            image_file.seek(0, os.SEEK_END)
            size = image_file.tell()
            image_file.seek(0)

            if size > MAX_DIAGRAM_FILE_SIZE:
                return jsonify({
                    "success": False,
                    "message": "Image is too large. Maximum allowed size is 10 MB."
                }), 400

            try:
                img_check = Image.open(image_file.stream)
                img_check.verify()
                image_file.stream.seek(0)
            except Exception:
                return jsonify({
                    "success": False,
                    "message": "The uploaded file is not a valid image."
                }), 400

            saved_path = save_uploaded_file(image_file, user_id)
            session["last_diagram_path"] = saved_path
            session["last_diagram_name"] = secure_filename(image_file.filename)

            active_file_path = saved_path
            diagram_filename = session["last_diagram_name"]

        elif session.get("last_diagram_path") and os.path.exists(session.get("last_diagram_path")):
            active_file_path = session.get("last_diagram_path")
            diagram_filename = session.get("last_diagram_name", "diagram")

        else:
            return jsonify({
                "success": False,
                "message": "Please attach a diagram image (PNG, JPG, JPEG) to explain."
            }), 400

        with Image.open(active_file_path) as img:
            image_copy = img.copy()

        explanation = generate_diagram_explanation(image_copy, question)

        return jsonify({
            "success": True,
            "answer": explanation,
            "diagram": True,
            "filename": diagram_filename
        })

    except Exception as error:
        print("DIAGRAM EXPLAINER ERROR:", error)
        return jsonify({
            "success": False,
            "message": f"Diagram explanation failed: {str(error)}"
        }), 500


@app.route("/api/ask/diagram/clear", methods=["POST"])
@login_required
def clear_diagram_context():
    session.pop("last_diagram_path", None)
    session.pop("last_diagram_name", None)
    return jsonify({
        "success": True,
        "message": "Diagram context cleared."
    })


# =========================================================
# QUIZ GENERATION
# =========================================================

@app.route("/api/quiz", methods=["POST"])
@login_required
def generate_quiz():
    try:
        user_id = get_logged_in_user_id()

        study_material = search_knowledge(
            "important concepts definitions key topics",
            top_k=15,
            user_id=user_id
        )

        if not study_material:
            return jsonify({
                "success": False,
                "message": "Please upload and process study materials first."
            }), 400

        context_parts = []

        for item in study_material:
            source = item.get("source", "UNKNOWN")
            text = item.get("text", "")

            if source == "PDF":
                reference = f"PDF Page {item.get('page', '?')}"
            elif source == "PPT":
                reference = f"PPT Slide {item.get('slide', '?')}"
            elif source == "VIDEO":
                reference = (
                    f"VIDEO {item.get('start', 0)}s - "
                    f"{item.get('end', 0)}s"
                )
            else:
                reference = source

            context_parts.append(f"[{reference}]\n{text}")

        context = "\n\n".join(context_parts)

        prompt = f"""
Generate exactly 5 multiple-choice questions for Bharat Study Buddy.
Use ONLY the study material below. Do not use outside knowledge.
Return ONLY valid JSON without Markdown fences.

Format:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": 0,
      "explanation": "Short explanation"
    }}
  ]
}}

Rules:
- Exactly 5 questions.
- Exactly 4 options per question.
- answer is the zero-based index of the correct option.
- Keep questions suitable for an MCA student.
- Do not invent information.
- Keep explanations short.

STUDY MATERIAL:
{context}
"""

        response = client.responses.create(
            model=GROQ_MODEL,
            input=prompt
        )

        quiz_data = clean_json_response(response.output_text)
        questions = quiz_data.get("questions", [])

        if len(questions) != 5:
            raise ValueError("AI did not generate exactly 5 questions.")

        for question in questions:
            if (
                not isinstance(question, dict)
                or not isinstance(question.get("options"), list)
                or len(question["options"]) != 4
                or not isinstance(question.get("answer"), int)
                or not 0 <= question["answer"] < 4
            ):
                raise ValueError("AI generated an invalid quiz format.")

        return jsonify({
            "success": True,
            "questions": questions
        })

    except Exception as error:
        print("QUIZ GENERATION ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Quiz generation failed. Please try again."
        }), 500


# =========================================================
# ADAPTIVE QUIZ
# =========================================================

@app.route("/api/adaptive-quiz", methods=["POST"])
@login_required
def generate_adaptive_quiz():
    try:
        data = request.get_json(silent=True) or {}
        wrong_questions = data.get("wrongQuestions", [])

        if not wrong_questions:
            return jsonify({
                "success": False,
                "message": "No weak topics found. Great job!"
            }), 400

        wrong_text = "\n\n".join(
            f"Question: {item.get('question', '')}\n"
            f"Student answer: {item.get('selectedAnswer', '')}\n"
            f"Correct answer: {item.get('correctAnswer', '')}\n"
            f"Explanation: {item.get('explanation', '')}"
            for item in wrong_questions
            if isinstance(item, dict)
        )

        prompt = f"""
You are an adaptive AI tutor for Bharat Study Buddy.
Analyze the incorrect answers and generate 3 new MCQs focused on
the weak topic. Use only information supported by the supplied context.
Return ONLY valid JSON without Markdown fences.

Format:
{{
  "weak_topic": "topic name",
  "questions": [
    {{
      "question": "Question",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": 0,
      "explanation": "Short explanation"
    }}
  ]
}}

Generate exactly 3 questions with 4 options each.
The answer is the zero-based correct option index.

INCORRECT QUIZ ANSWERS:
{wrong_text}
"""

        response = client.responses.create(
            model=GROQ_MODEL,
            input=prompt
        )

        result = clean_json_response(response.output_text)
        questions = result.get("questions", [])

        if len(questions) != 3:
            raise ValueError("AI did not generate exactly 3 questions.")

        for question in questions:
            if (
                not isinstance(question, dict)
                or not isinstance(question.get("options"), list)
                or len(question["options"]) != 4
                or not isinstance(question.get("answer"), int)
                or not 0 <= question["answer"] < 4
            ):
                raise ValueError("AI generated an invalid adaptive quiz format.")

        return jsonify({
            "success": True,
            "weak_topic": result.get("weak_topic", "Needs more practice"),
            "questions": questions
        })

    except Exception as error:
        print("ADAPTIVE QUIZ ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Adaptive quiz failed. Please try again."
        }), 500


# =========================================================
# SMART NOTES
# =========================================================

@app.route("/api/notes", methods=["POST"])
@login_required
def generate_notes():
    try:
        user_id = get_logged_in_user_id()

        sources = search_knowledge(
            "important concepts definitions key topics explanations",
            top_k=15,
            user_id=user_id
        )

        if not sources:
            return jsonify({
                "success": False,
                "message": "No study material found. Please upload and process your materials first."
            }), 400

        context_parts = []

        for source in sources:
            source_type = source.get("source", "SOURCE")
            text = source.get("text", "")

            if not text:
                continue

            if source_type == "PDF":
                reference = f"PDF Page {source.get('page', '?')}"
            elif source_type == "PPT":
                reference = f"PPT Slide {source.get('slide', '?')}"
            elif source_type == "VIDEO":
                reference = f"Video {source.get('start', 0)}s"
            else:
                reference = source_type

            context_parts.append(f"[{reference}]\n{text}")

        context = "\n\n".join(context_parts)

        prompt = f"""
You are Bharat Study Buddy, an AI study-notes generator.
Create concise, student-friendly notes ONLY from the material below.
Do not add outside information.

Include topic headings, important concepts, key points,
definitions, and quick revision points.
Cite sources after important points.
Return ONLY valid JSON without Markdown fences.

Format:
{{
  "title": "Study Notes",
  "notes": [
    {{
      "heading": "Topic",
      "points": ["Point one [PDF Page 2]"]
    }}
  ]
}}

STUDY MATERIAL:
{context}
"""

        response = client.responses.create(
            model=GROQ_MODEL,
            input=prompt
        )

        notes_data = clean_json_response(response.output_text)

        return jsonify({
            "success": True,
            "title": notes_data.get("title", "Study Notes"),
            "notes": notes_data.get("notes", [])
        })

    except Exception as error:
        print("SMART NOTES ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Smart Notes generation failed. Please try again."
        }), 500


# =========================================================
# SIGNUP
# =========================================================
# SIGNUP: SEND EMAIL OTP (GMAIL SMTP)
# =========================================================

def send_otp_email(to_email, recipient_name, otp):
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com").strip()
    mail_port = int(os.getenv("MAIL_PORT", "587").strip() or 587)
    mail_use_tls = os.getenv("MAIL_USE_TLS", "true").strip().lower() in ("true", "1", "yes")
    mail_username = os.getenv("MAIL_USERNAME", "").strip()
    mail_password = os.getenv("MAIL_PASSWORD", "").strip()
    mail_sender = os.getenv("MAIL_DEFAULT_SENDER", "").strip() or mail_username

    if not mail_username or not mail_password:
        raise ValueError("Email credentials not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Bharat Study Buddy - Email Verification Code"
    msg["From"] = f"Bharat Study Buddy <{mail_sender}>" if mail_sender else mail_username
    msg["To"] = to_email

    text_content = (
        f"Hello {recipient_name},\n\n"
        f"Your Bharat Study Buddy verification code is: {otp}\n\n"
        "This code expires in 5 minutes. Please do not share it with anyone.\n\n"
        "-- Bharat Study Buddy"
    )
    html_content = (
        f"<div style='font-family: Arial, sans-serif; line-height: 1.6; color: #24213d; max-width: 480px; padding: 20px; border: 1px solid #e2e0f0; border-radius: 12px;'>"
        f"<h2 style='color: #5145cd; margin-bottom: 12px;'>Bharat Study Buddy</h2>"
        f"<p>Hello <strong>{escape(recipient_name)}</strong>,</p>"
        f"<p>Your email verification code is:</p>"
        f"<div style='font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #5145cd; padding: 12px 18px; background: #f1efff; border-radius: 8px; display: inline-block; margin: 12px 0;'>"
        f"{otp}"
        f"</div>"
        f"<p style='color: #666; font-size: 14px; margin-top: 15px;'>This code expires in 5 minutes. Please do not share it with anyone.</p>"
        f"</div>"
    )

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
        if mail_use_tls:
            server.starttls()
        server.login(mail_username, mail_password)
        server.send_message(msg)


@app.route("/api/auth/send-otp", methods=["POST"])
def send_signup_otp():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name or not email or not isinstance(password, str) or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required."
        }), 400

    if len(name) > 100 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        return jsonify({
            "success": False,
            "message": "Please enter a valid name and email."
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters."
        }), 400

    dev_mode = os.getenv("OTP_DEV_MODE", "false").strip().lower() == "true"
    mail_username = os.getenv("MAIL_USERNAME", "").strip()
    mail_password = os.getenv("MAIL_PASSWORD", "").strip()

    if not dev_mode and (not mail_username or not mail_password):
        return jsonify({
            "success": False,
            "message": "Email service is not configured. Check the server .env file."
        }), 500

    connection = get_connection()
    now = int(time.time())

    try:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            return jsonify({
                "success": False,
                "message": "This email is already registered. Please log in."
            }), 409

        pending = connection.execute(
            "SELECT last_sent_at FROM pending_signups WHERE email = ?",
            (email,)
        ).fetchone()

        if pending and now - pending["last_sent_at"] < 60:
            wait = 60 - (now - pending["last_sent_at"])
            return jsonify({
                "success": False,
                "message": f"Please wait {wait} seconds before requesting another code."
            }), 429

        otp = f"{secrets.randbelow(1000000):06d}"

        if dev_mode:
            print(f"\n[DEVELOPMENT OTP] Email: {email} | Code: {otp}\n")
            success_message = (
                "Development mode: code printed in the backend terminal. "
                "Check the terminal running backend/app.py."
            )
        else:
            try:
                send_otp_email(email, name, otp)
                success_message = "Verification code sent to your email."
            except smtplib.SMTPAuthenticationError:
                print("SMTP AUTHENTICATION ERROR: Invalid Gmail credentials.")
                return jsonify({
                    "success": False,
                    "message": "Email authentication failed. Please check your Gmail App Password."
                }), 502
            except smtplib.SMTPRecipientsRefused:
                print("SMTP RECIPIENT ERROR: Recipient address rejected.")
                return jsonify({
                    "success": False,
                    "message": "Recipient email address was rejected by the mail server."
                }), 400
            except Exception as error:
                print("SMTP EMAIL ERROR:", type(error).__name__)
                return jsonify({
                    "success": False,
                    "message": "Failed to send verification email. Please try again."
                }), 502

        connection.execute("""
            INSERT INTO pending_signups
                (email, name, password_hash, otp_hash,
                 expires_at, attempts, last_sent_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                password_hash = excluded.password_hash,
                otp_hash = excluded.otp_hash,
                expires_at = excluded.expires_at,
                attempts = 0,
                last_sent_at = excluded.last_sent_at
        """, (
            email,
            name,
            generate_password_hash(password),
            generate_password_hash(otp),
            now + 300,
            now
        ))

        connection.commit()

        return jsonify({
            "success": True,
            "message": success_message,
            "email": email
        }), 200

    except Exception as error:
        connection.rollback()
        print("SEND OTP ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not start signup. Please try again."
        }), 500

    finally:
        connection.close()


# =========================================================
# SIGNUP: VERIFY OTP AND CREATE ACCOUNT
# =========================================================

@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_signup_otp():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not re.fullmatch(r"\d{6}", otp):
        return jsonify({
            "success": False,
            "message": "Enter the 6-digit verification code."
        }), 400

    connection = get_connection()

    try:
        pending = connection.execute(
            "SELECT * FROM pending_signups WHERE email = ?",
            (email,)
        ).fetchone()

        if not pending:
            return jsonify({
                "success": False,
                "message": "Signup request not found. Please request a new code."
            }), 400

        now = int(time.time())

        if now >= pending["expires_at"]:
            connection.execute(
                "DELETE FROM pending_signups WHERE email = ?", (email,)
            )
            connection.commit()

            return jsonify({
                "success": False,
                "message": "Code expired. Please request a new code."
            }), 400

        if pending["attempts"] >= 5:
            connection.execute(
                "DELETE FROM pending_signups WHERE email = ?", (email,)
            )
            connection.commit()

            return jsonify({
                "success": False,
                "message": "Too many incorrect attempts. Please request a new code."
            }), 429

        if not check_password_hash(pending["otp_hash"], otp):
            connection.execute("""
                UPDATE pending_signups
                SET attempts = attempts + 1
                WHERE email = ?
            """, (email,))
            connection.commit()

            return jsonify({
                "success": False,
                "message": "Incorrect verification code."
            }), 400

        connection.execute("""
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
        """, (
            pending["name"],
            pending["email"],
            pending["password_hash"]
        ))

        connection.execute(
            "DELETE FROM pending_signups WHERE email = ?", (email,)
        )
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Email verified and account created. Please log in."
        }), 201

    except sqlite3.IntegrityError:
        connection.rollback()
        return jsonify({
            "success": False,
            "message": "This email is already registered. Please log in."
        }), 409

    except Exception as error:
        connection.rollback()
        print("VERIFY OTP ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not verify the code. Please try again."
        }), 500

    finally:
        connection.close()


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id, name, email, password FROM users WHERE email = ?",
            (email,)
        ).fetchone()
    finally:
        connection.close()

    if user is None or not check_password_hash(user["password"], password):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }), 200


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200


# =========================================================
# CURRENT USER
# =========================================================

@app.route("/api/auth/me", methods=["GET"])
def current_user():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Not logged in."
        }), 401

    return jsonify({
        "success": True,
        "user": {
            "id": session["user_id"],
            "name": session["user_name"],
            "email": session["user_email"]
        }
    }), 200


# =========================================================
# START SERVER
# =========================================================

# =========================================================
# STUDY PLANNER
# =========================================================

from datetime import date, datetime, timedelta


@app.route("/api/study-planner/plans", methods=["GET"])
@login_required
def get_study_plans():
    user_id = get_logged_in_user_id()
    connection = get_connection()

    try:
        plans = connection.execute("""
            SELECT
                p.*,
                COUNT(t.id) AS total_tasks,
                COALESCE(SUM(t.is_completed), 0) AS completed_tasks
            FROM study_plans p
            LEFT JOIN study_tasks t ON t.plan_id = p.id
            WHERE p.user_id = ?
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """, (user_id,)).fetchall()

        result = []

        for plan in plans:
            item = dict(plan)
            item["subjects"] = json.loads(item["subjects"])
            item["weak_subjects"] = json.loads(item["weak_subjects"])
            total = item["total_tasks"]
            item["progress"] = round(
                item["completed_tasks"] * 100 / total
            ) if total else 0
            result.append(item)

        return jsonify({"success": True, "plans": result})

    except Exception as error:
        print("STUDY PLANS ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not load study plans."
        }), 500

    finally:
        connection.close()


@app.route("/api/study-planner/generate", methods=["POST"])
@login_required
def generate_study_plan():
    connection = None

    try:
        data = request.get_json(silent=True) or {}

        subjects = data.get("subjects", [])
        exam_date = data.get("exam_date", "")
        daily_hours = data.get("daily_hours", 3)
        weak_subjects = data.get("weak_subjects", [])
        topics = data.get("topics", [])

        if isinstance(subjects, str):
            subjects = [s.strip() for s in subjects.split(",") if s.strip()]

        if not isinstance(subjects, list) or not subjects:
            return jsonify({
                "success": False,
                "message": "Please enter at least one subject."
            }), 400

        subjects = [
            s.strip() for s in subjects
            if isinstance(s, str) and s.strip()
        ]

        if not subjects:
            return jsonify({
                "success": False,
                "message": "Please enter valid subjects."
            }), 400

        if len(subjects) > 20:
            return jsonify({
                "success": False,
                "message": "Please enter at most 20 subjects."
            }), 400

        try:
            exam_day = date.fromisoformat(exam_date)
            hours = float(daily_hours)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Enter a valid exam date and daily study hours."
            }), 400

        if exam_day <= date.today():
            return jsonify({
                "success": False,
                "message": "Exam date must be in the future."
            }), 400

        if not 1 <= hours <= 16:
            return jsonify({
                "success": False,
                "message": "Daily study hours must be between 1 and 16."
            }), 400

        if not isinstance(weak_subjects, list):
            weak_subjects = []

        if not isinstance(topics, list):
            topics = []

        if len(topics) > 200:
            return jsonify({
                "success": False,
                "message": "Please provide at most 200 topics."
            }), 400

        start_day = date.today() + timedelta(days=1)
        study_days = (exam_day - start_day).days + 1

        if study_days < 1:
            return jsonify({
                "success": False,
                "message": "There are no study days before the exam."
            }), 400

        prompt = f"""
You are an expert study planner.

Create a practical day-by-day study timetable for a student.

Subjects: {json.dumps(subjects)}
Topics provided by student: {json.dumps(topics)}
Weak subjects: {json.dumps(weak_subjects)}
Daily study hours: {hours}
First study date: {start_day.isoformat()}
Exam date: {exam_day.isoformat()}
Number of available study days: {study_days}

Return ONLY valid JSON, without Markdown fences, in this format:
{{
  "title": "Study Plan",
  "tasks": [
    {{
      "date": "{start_day.isoformat()}",
      "subject": "Subject name",
      "topic": "Topic to study",
      "start_time": "18:00",
      "duration_minutes": 60
    }}
  ]
}}

Rules:
- Schedule tasks only between the first study date and exam date.
- Include revision and practice before the exam.
- Prioritize weak subjects but cover all subjects.
- Do not exceed the available daily study hours.
- Use 30 to 180 minutes per task.
- Use ISO dates YYYY-MM-DD and 24-hour start times.
- Keep topic names concise and realistic.
- Do not invent a syllabus when topics are supplied; use the supplied topics.
- Generate a manageable timetable, with no more than 8 tasks per day.
"""

        response = client.responses.create(
            model=GROQ_MODEL,
            input=prompt
        )

        plan_data = clean_json_response(response.output_text)
        tasks = plan_data.get("tasks", [])

        if not isinstance(tasks, list) or not tasks:
            raise ValueError("AI returned no study tasks.")

        if len(tasks) > min(study_days * 8, 1000):
            raise ValueError("AI returned too many tasks.")

        valid_tasks = []

        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_date = date.fromisoformat(task.get("date", ""))
            subject = task.get("subject", "")
            topic = task.get("topic", "")
            start_time = task.get("start_time", "")
            duration = int(task.get("duration_minutes", 60))

            if not start_day <= task_date <= exam_day:
                continue

            if not isinstance(subject, str) or subject not in subjects:
                continue

            if not isinstance(topic, str) or not topic.strip():
                continue

            if not 30 <= duration <= 180:
                continue

            try:
                datetime.strptime(start_time, "%H:%M")
            except (ValueError, TypeError):
                start_time = ""

            valid_tasks.append((
                task_date.isoformat(),
                subject,
                topic.strip(),
                start_time,
                duration
            ))

        if not valid_tasks:
            raise ValueError("AI returned no valid tasks.")

        connection = get_connection()
        user_id = get_logged_in_user_id()

        cursor = connection.execute("""
            INSERT INTO study_plans
                (user_id, title, subjects, exam_date, daily_hours, weak_subjects)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            str(plan_data.get("title", "My Study Plan"))[:150],
            json.dumps(subjects),
            exam_day.isoformat(),
            hours,
            json.dumps(weak_subjects)
        ))

        plan_id = cursor.lastrowid

        connection.executemany("""
            INSERT INTO study_tasks
                (plan_id, user_id, task_date, subject, topic,
                 start_time, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (plan_id, user_id, *task)
            for task in valid_tasks
        ])

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Study plan generated and saved.",
            "plan_id": plan_id,
            "title": plan_data.get("title", "My Study Plan"),
            "tasks_created": len(valid_tasks)
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        print("STUDY PLAN GENERATION ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not generate the study plan. Please try again."
        }), 500

    finally:
        if connection:
            connection.close()


@app.route("/api/study-planner/plans/<int:plan_id>", methods=["GET"])
@login_required
def get_study_plan_details(plan_id):
    user_id = get_logged_in_user_id()
    connection = get_connection()

    try:
        plan = connection.execute("""
            SELECT * FROM study_plans
            WHERE id = ? AND user_id = ?
        """, (plan_id, user_id)).fetchone()

        if not plan:
            return jsonify({
                "success": False,
                "message": "Study plan not found."
            }), 404

        tasks = connection.execute("""
            SELECT * FROM study_tasks
            WHERE plan_id = ? AND user_id = ?
            ORDER BY task_date, start_time, id
        """, (plan_id, user_id)).fetchall()

        return jsonify({
            "success": True,
            "plan": dict(plan),
            "tasks": [dict(task) for task in tasks]
        })

    except Exception as error:
        print("STUDY PLAN DETAILS ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not load study plan."
        }), 500

    finally:
        connection.close()


@app.route("/api/study-planner/tasks/<int:task_id>", methods=["PATCH"])
@login_required
def update_study_task(task_id):
    data = request.get_json(silent=True) or {}
    completed = data.get("is_completed")

    if not isinstance(completed, bool):
        return jsonify({
            "success": False,
            "message": "is_completed must be true or false."
        }), 400

    connection = get_connection()
    user_id = get_logged_in_user_id()

    try:
        cursor = connection.execute("""
            UPDATE study_tasks
            SET is_completed = ?,
                completed_at = CASE
                    WHEN ? = 1 THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE id = ? AND user_id = ?
        """, (int(completed), int(completed), task_id, user_id))

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Task not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Task updated."
        })

    except Exception as error:
        connection.rollback()
        print("STUDY TASK UPDATE ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not update task."
        }), 500

    finally:
        connection.close()


@app.route("/api/study-planner/plans/<int:plan_id>", methods=["DELETE"])
@login_required
def delete_study_plan(plan_id):
    connection = get_connection()
    user_id = get_logged_in_user_id()

    try:
        cursor = connection.execute("""
            DELETE FROM study_plans
            WHERE id = ? AND user_id = ?
        """, (plan_id, user_id))

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Study plan not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Study plan deleted."
        })

    except Exception as error:
        connection.rollback()
        print("STUDY PLAN DELETE ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not delete study plan."
        }), 500

    finally:
        connection.close()

if __name__ == "__main__":
    init_database()
    app.run(debug=True, port=5000)
