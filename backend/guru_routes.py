"""
Guru AI Voice Assistant — API Blueprint Routes
Bharat Study Buddy

Endpoints:
- POST   /api/guru/intro-chat      (Public: Index Page Guru)
- POST   /api/guru/chat            (Auth: Dashboard Personal Guru)
- POST   /api/guru/transcribe      (Auth: Groq Whisper Voice STT)
- POST   /api/guru/tts             (Public/Auth: Hindi/English Voice TTS Stream)
- GET    /api/guru/context         (Auth: Dashboard Guru Context Summary)
- GET    /api/guru/exam-dates      (Auth: List student exam dates with remaining days)
- POST   /api/guru/exam-dates      (Auth: Save student exam date)
- DELETE /api/guru/exam-dates/<id> (Auth: Delete student exam date)
- POST   /api/guru/paper-analyzer  (Auth: Analyze papers/syllabus for repeated questions)
- POST   /api/guru/notes           (Auth: Smart notes generator)
- POST   /api/guru/flashcards      (Auth: Flashcard generator)
- POST   /api/guru/practice-paper  (Auth: Practice mock paper generator)
"""

import io
from functools import wraps
from flask import Blueprint, request, jsonify, session, Response

from guru_service import (
    chat_index_guru,
    chat_dashboard_guru,
    transcribe_audio_bytes,
    synthesize_speech,
    get_student_info,
    get_exam_dates,
    save_exam_date,
    delete_exam_date,
    get_study_plans_summary,
    analyze_student_papers,
    generate_guru_smart_notes,
    generate_guru_flashcards,
    generate_guru_practice_paper
)

guru_bp = Blueprint("guru", __name__, url_prefix="/api/guru")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "success": False,
                "message": "Please log in to access Dashboard Guru."
            }), 401
        return f(*args, **kwargs)
    return decorated_function


# =========================================================
# 1. INDEX PAGE GURU: PUBLIC INTRODUCTION CHAT
# =========================================================

@guru_bp.route("/intro-chat", methods=["POST"])
def intro_chat():
    """
    Public conversational endpoint for the index/landing page.
    Introduces Bharat Study Buddy, its features, and registration guide.
    STRICTLY isolated from authenticated student files and private data.
    """
    try:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({
                "success": False,
                "message": "Message is required."
            }), 400

        result = chat_index_guru(user_message=message, history=history)
        return jsonify({
            "success": True,
            "reply": result.get("reply", ""),
            "mode": result.get("mode", "intro")
        }), 200

    except Exception as error:
        print("GURU INTRO CHAT ROUTE ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Guru introduction service unavailable."
        }), 500


# =========================================================
# 2. DASHBOARD GURU: PERSONAL VOICE & TEXT CHAT
# =========================================================

@guru_bp.route("/chat", methods=["POST"])
@login_required
def dashboard_chat():
    """
    Conversational brain for Dashboard Guru.
    Takes student's voice or text question, retrieves relevant uploaded materials (RAG),
    checks upcoming exam dates and active study plans, and responds in Hindi/English/Hinglish.
    """
    try:
        user_id = session["user_id"]
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({
                "success": False,
                "message": "Message is required."
            }), 400

        result = chat_dashboard_guru(
            user_id=user_id,
            user_message=message,
            history=history
        )

        return jsonify({
            "success": True,
            "reply": result.get("reply", ""),
            "sources": result.get("sources", []),
            "student_name": result.get("student_name", "Student"),
            "exam_dates": result.get("exam_dates", [])
        }), 200

    except Exception as error:
        print("GURU DASHBOARD CHAT ROUTE ERROR:", error)
        return jsonify({
            "success": False,
            "message": f"Guru chat error: {str(error)}"
        }), 500


# =========================================================
# 3. SPEECH TO TEXT: GROQ WHISPER
# =========================================================

@guru_bp.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """
    Receives recorded audio from student microphone and transcribes via Groq Whisper.
    Works for both index assistant and dashboard assistant.
    """
    try:
        if "audio" not in request.files and "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "No audio file provided."
            }), 400

        audio_file = request.files.get("audio") or request.files.get("file")
        if not audio_file or not audio_file.filename:
            return jsonify({
                "success": False,
                "message": "Empty audio recording."
            }), 400

        audio_bytes = audio_file.read()
        if len(audio_bytes) < 100:
            return jsonify({
                "success": False,
                "message": "Audio recording too short or empty."
            }), 400

        transcribed_text = transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=audio_file.filename or "recording.webm"
        )

        return jsonify({
            "success": True,
            "text": transcribed_text
        }), 200

    except Exception as error:
        print("GURU TRANSCRIBE ROUTE ERROR:", error)
        return jsonify({
            "success": False,
            "message": f"Transcription error: {str(error)}"
        }), 500


# =========================================================
# 4. TEXT TO SPEECH: HINDI & INDIAN-ENGLISH STREAM
# =========================================================

@guru_bp.route("/tts", methods=["POST", "GET"])
def tts_stream():
    """
    Synthesizes speech into natural MP3 audio using gTTS (Hindi / Indian English).
    Returns audio/mpeg stream directly playable by HTML5 Audio.
    """
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            text = data.get("text", "").strip()
            lang = data.get("lang")
        else:
            text = request.args.get("text", "").strip()
            lang = request.args.get("lang")

        if not text:
            return jsonify({
                "success": False,
                "message": "Text parameter is required."
            }), 400

        audio_bytes = synthesize_speech(text, lang=lang)

        return Response(
            audio_bytes,
            mimetype="audio/mpeg",
            headers={
                "Content-Type": "audio/mpeg",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": "inline; filename=guru_speech.mp3"
            }
        )

    except Exception as error:
        print("GURU TTS ROUTE ERROR:", error)
        return jsonify({
            "success": False,
            "message": f"Speech synthesis failed: {str(error)}"
        }), 500


# =========================================================
# 5. DASHBOARD GURU CONTEXT
# =========================================================

@guru_bp.route("/context", methods=["GET"])
@login_required
def get_guru_context():
    """Returns aggregated student data for Dashboard Guru UI."""
    try:
        user_id = session["user_id"]
        student = get_student_info(user_id)
        exams = get_exam_dates(user_id)
        planner = get_study_plans_summary(user_id)

        return jsonify({
            "success": True,
            "student": student,
            "exam_dates": exams,
            "study_plans": planner.get("plans", []),
            "today_tasks": planner.get("today_tasks", [])
        }), 200

    except Exception as error:
        print("GURU CONTEXT ROUTE ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not load Guru context."
        }), 500


# =========================================================
# 6. EXAM DATE MANAGEMENT
# =========================================================

@guru_bp.route("/exam-dates", methods=["GET"])
@login_required
def list_exam_dates():
    try:
        user_id = session["user_id"]
        dates = get_exam_dates(user_id)
        return jsonify({"success": True, "exam_dates": dates}), 200
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@guru_bp.route("/exam-dates", methods=["POST"])
@login_required
def add_exam_date():
    try:
        user_id = session["user_id"]
        data = request.get_json(silent=True) or {}
        subject = data.get("subject", "").strip()
        exam_date_str = data.get("exam_date", "").strip()
        notes = data.get("notes", "").strip()

        if not subject or not exam_date_str:
            return jsonify({
                "success": False,
                "message": "Subject and exam date (YYYY-MM-DD) are required."
            }), 400

        exam_id = save_exam_date(user_id, subject, exam_date_str, notes)
        return jsonify({
            "success": True,
            "message": f"Exam date for {subject} saved successfully.",
            "exam_id": exam_id
        }), 201

    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@guru_bp.route("/exam-dates/<int:exam_id>", methods=["DELETE"])
@login_required
def remove_exam_date(exam_id):
    try:
        user_id = session["user_id"]
        delete_exam_date(user_id, exam_id)
        return jsonify({"success": True, "message": "Exam date removed."}), 200
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


# =========================================================
# 7. PAPER ANALYZER
# =========================================================

@guru_bp.route("/paper-analyzer", methods=["POST"])
@login_required
def paper_analyzer():
    try:
        user_id = session["user_id"]
        data = request.get_json(silent=True) or {}
        subject = data.get("subject", "").strip()

        result = analyze_student_papers(user_id, subject=subject or None)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as error:
        print("GURU PAPER ANALYZER ERROR:", error)
        return jsonify({"success": False, "message": str(error)}), 500


# =========================================================
# 8. SMART NOTES
# =========================================================

@guru_bp.route("/notes", methods=["POST"])
@login_required
def smart_notes():
    try:
        user_id = session["user_id"]
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "").strip()

        result = generate_guru_smart_notes(user_id, topic=topic or None)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as error:
        print("GURU SMART NOTES ERROR:", error)
        return jsonify({"success": False, "message": str(error)}), 500


# =========================================================
# 9. FLASHCARDS
# =========================================================

@guru_bp.route("/flashcards", methods=["POST"])
@login_required
def flashcards():
    try:
        user_id = session["user_id"]
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "").strip()

        result = generate_guru_flashcards(user_id, topic=topic or None)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as error:
        print("GURU FLASHCARDS ERROR:", error)
        return jsonify({"success": False, "message": str(error)}), 500


# =========================================================
# 10. PRACTICE PAPER GENERATOR
# =========================================================

@guru_bp.route("/practice-paper", methods=["POST"])
@login_required
def practice_paper():
    try:
        user_id = session["user_id"]
        data = request.get_json(silent=True) or {}
        subject = data.get("subject", "").strip()
        paper_type = data.get("paper_type", "mcq").strip().lower()

        result = generate_guru_practice_paper(user_id, subject=subject or None, paper_type=paper_type)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as error:
        print("GURU PRACTICE PAPER ERROR:", error)
        return jsonify({"success": False, "message": str(error)}), 500
