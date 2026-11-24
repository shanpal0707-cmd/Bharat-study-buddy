"""
Guru AI Voice Assistant — Core Service Module
Bharat Study Buddy

Provides:
- Groq LLM reasoning (openai/gpt-oss-120b)
- Groq Whisper speech-to-text (whisper-large-v3-turbo)
- Genuinely Hindi & Indian-English TTS audio synthesis (gTTS)
- Retrieval-Augmented Generation (RAG) over student materials
- Paper Analyzer reasoning
- AI Study Planner integration
- Exam date tracking & awareness
- Smart Notes, Flashcards & Practice Papers generation
- Index Page Introduction Assistant logic
"""

import os
import io
import re
import json
import time
from datetime import date, datetime, timedelta
import requests
from dotenv import load_dotenv
from openai import OpenAI
from gtts import gTTS

from database import get_connection
from knowledge_base import search_knowledge, load_knowledge_base

# Load environment configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Initialize Groq client
client = None
if GROQ_API_KEY:
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )


# =========================================================
# HELPER: CLEAN JSON
# =========================================================

def clean_json_response(raw_text):
    """Safely extract valid JSON from LLM output, stripping markdown fences or extracting outermost JSON object."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except Exception:
        # Try extracting outermost { ... } or [ ... ]
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw_text)
        if match:
            return json.loads(match.group(1).strip())
        raise


def strip_markdown_for_tts(text):
    """Removes markdown syntax, URLs and bullets so spoken audio sounds natural."""
    clean = re.sub(r"\[.*?\]\(.*?\)", "", text) # links
    clean = re.sub(r"\[.*?\]", "", clean)        # citations like [PDF Page 2]
    clean = re.sub(r"[*#_`~>]", "", clean)       # markdown styling symbols
    clean = re.sub(r"\n+", ". ", clean)          # newlines to pauses
    clean = re.sub(r"\s+", " ", clean).strip()   # normalize whitespace
    return clean


# =========================================================
# SPEECH TO TEXT: GROQ WHISPER
# =========================================================

def transcribe_audio_bytes(audio_bytes, filename="audio.webm"):
    """
    Transcribes student voice recordings using Groq Whisper (whisper-large-v3-turbo).
    Supports Hindi, English, and Hinglish.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured on the server.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    # Prepare multipart upload
    files = {
        "file": (filename, audio_bytes, "audio/webm")
    }
    data = {
        "model": "whisper-large-v3-turbo",
        "response_format": "json",
        "prompt": "Transcribe student educational questions in Hindi, English, or Hinglish for Bharat Study Buddy."
    }

    response = requests.post(
        GROQ_WHISPER_URL,
        headers=headers,
        data=data,
        files=files,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(f"Groq Whisper STT failed ({response.status_code}): {response.text}")

    result = response.json()
    return result.get("text", "").strip()


# =========================================================
# TEXT TO SPEECH: GENUINE HINDI & INDIAN-ENGLISH TTS
# =========================================================

def detect_language_for_tts(text):
    """
    Detects if text contains Devanagari script or common Hindi/Hinglish tokens,
    otherwise defaults to Indian English.
    """
    # Check for Devanagari Unicode block
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    # Common Hinglish words
    hinglish_markers = [
        r"\bpadhna\b", r"\bpadhai\b", r"\bhai\b", r"\bhein\b", r"\bhain\b",
        r"\bmera\b", r"\bmeri\b", r"\bmere\b", r"\baap\b", r"\bkya\b",
        r"\bkaise\b", r"\bbatao\b", r"\bkar\b", r"\bkaro\b", r"\bya\b",
        r"\baaj\b", r"\bkal\b", r"\bbaad\b", r"\bnamaste\b", r"\bdost\b",
        r"\btopics\b", r"\bexam\b", r"\btaiyyari\b"
    ]
    matches = sum(1 for pattern in hinglish_markers if re.search(pattern, text, re.IGNORECASE))
    if matches >= 2:
        return "hi"

    return "en"


def synthesize_speech(text, lang=None):
    """
    Converts Guru's written text into spoken audio stream (MP3) using gTTS.
    Uses 'hi' for Hindi/Hinglish and 'en' with Indian domain (tld='co.in') for English.
    Returns bytes of MP3 audio.
    """
    clean_text = strip_markdown_for_tts(text)
    if not clean_text:
        clean_text = "Main sun raha hoon. Aapka sawaal kya hai?"

    # Keep spoken snippet reasonable length for quick streaming (max 500 chars per clip)
    if len(clean_text) > 600:
        clean_text = clean_text[:600] + "..."

    selected_lang = lang or detect_language_for_tts(clean_text)

    fp = io.BytesIO()
    if selected_lang == "hi":
        tts = gTTS(text=clean_text, lang="hi", slow=False)
    else:
        tts = gTTS(text=clean_text, lang="en", tld="co.in", slow=False)

    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()


# =========================================================
# STUDENT DATA ACCESS & EXAM DATE MANAGEMENT
# =========================================================

def get_student_info(user_id):
    """Retrieves student profile from users table."""
    conn = get_connection()
    try:
        user = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(user) if user else {"id": user_id, "name": "Student", "email": ""}
    finally:
        conn.close()


def get_exam_dates(user_id):
    """
    Retrieves all exam dates for the user from both guru_exam_dates and study_plans.
    Calculates remaining days and sorts by nearest upcoming date.
    """
    conn = get_connection()
    try:
        results = []
        today = date.today()

        # Query explicit guru_exam_dates
        dates_cursor = conn.execute("""
            SELECT id, subject, exam_date, notes, created_at
            FROM guru_exam_dates
            WHERE user_id = ?
            ORDER BY exam_date ASC
        """, (user_id,)).fetchall()

        seen_subjects = set()
        for row in dates_cursor:
            r = dict(row)
            try:
                target = date.fromisoformat(r["exam_date"])
                r["days_remaining"] = (target - today).days
                r["is_past"] = target < today
            except Exception:
                r["days_remaining"] = None
                r["is_past"] = False
            results.append(r)
            seen_subjects.add(r["subject"].strip().lower())

        # Also pull dates from study_plans if not already added
        plans_cursor = conn.execute("""
            SELECT id, title, subjects, exam_date
            FROM study_plans
            WHERE user_id = ?
            ORDER BY exam_date ASC
        """, (user_id,)).fetchall()

        for row in plans_cursor:
            p = dict(row)
            try:
                subjects_list = json.loads(p["subjects"])
                sub_title = ", ".join(subjects_list) if isinstance(subjects_list, list) else p["title"]
            except Exception:
                sub_title = p["title"]

            if sub_title.strip().lower() not in seen_subjects:
                try:
                    target = date.fromisoformat(p["exam_date"])
                    days = (target - today).days
                    is_past = target < today
                except Exception:
                    days = None
                    is_past = False
                results.append({
                    "id": f"plan_{p['id']}",
                    "subject": sub_title,
                    "exam_date": p["exam_date"],
                    "notes": "Linked to AI Study Plan",
                    "days_remaining": days,
                    "is_past": is_past
                })
                seen_subjects.add(sub_title.strip().lower())

        # Sort with upcoming exams first
        results.sort(key=lambda x: (x["is_past"], x["days_remaining"] if x["days_remaining"] is not None else 9999))
        return results
    finally:
        conn.close()


def save_exam_date(user_id, subject, exam_date_str, notes=""):
    """Saves or updates an exam date in guru_exam_dates."""
    # Validate date
    target = date.fromisoformat(exam_date_str)
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO guru_exam_dates (user_id, subject, exam_date, notes)
            VALUES (?, ?, ?, ?)
        """, (user_id, subject.strip(), target.isoformat(), notes.strip()))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def delete_exam_date(user_id, exam_id):
    """Deletes an exam date."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM guru_exam_dates WHERE id = ? AND user_id = ?", (exam_id, user_id))
        conn.commit()
    finally:
        conn.close()


def get_study_plans_summary(user_id):
    """Reads active study plans and tasks progress for the student."""
    conn = get_connection()
    try:
        plans = conn.execute("""
            SELECT p.id, p.title, p.subjects, p.exam_date, p.daily_hours, p.weak_subjects,
                   COUNT(t.id) AS total_tasks,
                   COALESCE(SUM(t.is_completed), 0) AS completed_tasks
            FROM study_plans p
            LEFT JOIN study_tasks t ON t.plan_id = p.id
            WHERE p.user_id = ?
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """, (user_id,)).fetchall()

        summary_list = []
        for p in plans:
            item = dict(p)
            try:
                item["subjects"] = json.loads(item["subjects"])
            except Exception:
                pass
            try:
                item["weak_subjects"] = json.loads(item["weak_subjects"])
            except Exception:
                pass
            total = item["total_tasks"]
            item["progress_percent"] = round(item["completed_tasks"] * 100 / total) if total else 0
            summary_list.append(item)

        # Get tasks scheduled for today
        today_iso = date.today().isoformat()
        todays_tasks = conn.execute("""
            SELECT id, plan_id, subject, topic, start_time, duration_minutes, is_completed
            FROM study_tasks
            WHERE user_id = ? AND task_date = ?
            ORDER BY start_time, id
        """, (user_id, today_iso)).fetchall()

        return {
            "plans": summary_list,
            "today_tasks": [dict(t) for t in todays_tasks]
        }
    finally:
        conn.close()


# =========================================================
# INDEX PAGE GURU: WEBSITE INTRODUCTION ASSISTANT
# =========================================================

INDEX_GURU_SYSTEM_PROMPT = """You are Guru, the friendly AI Guide and Welcome Assistant for Bharat Study Buddy.
Bharat Study Buddy is an AI-powered multimodal learning companion designed specifically for Indian college and school students (undergraduate, MCA, B.Tech, BCA, competitive exams).

Your ONLY responsibility is to welcome visitors, introduce the website, and explain its features warmly and clearly.

WEBSITE FEATURES YOU INTRODUCE:
1. 📚 Study Material Upload: Students can upload textbooks, notes (PDF), lecture slides (PPT/PPTX), and recorded lecture videos (MP4, WEBM).
2. 💬 Multimodal Ask AI: Students can ask conceptual questions and get answers grounded strictly in their uploaded materials, with source citations (PDF page, PPT slide, video timestamp). Also includes AI Diagram Explainer that deciphers technical diagrams (OS process states, TCP handshake, ER diagrams, data structures) step by step!
3. 📊 Paper Analyzer: Analyzes previous years' question papers and syllabus guides to highlight repeated questions, exam patterns, marks distribution, and high-priority topics.
4. 📅 AI Study Planner: Generates a day-by-day personalized timetable leading up to exam day, taking into account subjects, weak topics, and daily available study hours, with live task completion tracking.
5. 📒 Smart Notes: Turns voluminous study materials into structured revision notes, key formulas, unit summaries, and definitions.
6. 📇 Flashcards: Generates interactive question-and-answer revision cards with active recall practice.
7. 🎙️ Video Lecture Transcription: Transcribes recorded lecture videos with timestamps into searchable notes using AI.
8. 🤖 Dashboard Guru: The personal AI voice assistant on the student's private dashboard. It supports continuous voice conversation in Hindi, English, and Hinglish, knows their exam dates, answers doubts, and guides daily study.

HOW STUDENTS GET STARTED:
- Click 'Get Started' or 'Start Learning' on the top navbar.
- Enter Name, Email, and Password.
- Receive a secure 6-digit OTP code in their email (valid for 5 minutes).
- Enter OTP and log in to access their personalized study space.

PERSONALITY & LANGUAGE:
- Friendly, encouraging, polite Indian tutor persona ("Namaste! I'm Guru...").
- Fluently responds in English, Hindi, or Hinglish depending on what the user speaks or writes.
- Always keep answers concise, neat, and formatted with bullet points or emojis.

STRICT RESTRICTIONS:
- You DO NOT have access to private student files, uploaded PDFs, or authenticated dashboard data.
- If a user asks you to read their personal notes, analyze their specific exam, or prepare a personal schedule, politely explain:
  "I am the Website Introduction Guru. To analyze your private notes, generate your personal study plan, or chat with continuous voice, please log in to the Dashboard where your Personal Dashboard Guru is waiting for you!"
"""

def chat_index_guru(user_message, history=None):
    """
    Handles visitor conversations on the index/landing page.
    Explains Bharat Study Buddy features, registration, and usage.
    """
    if not client:
        return {
            "reply": "Namaste! I'm Guru, your AI guide. Welcome to Bharat Study Buddy! Please make sure the Groq API key is configured on the backend.",
            "mode": "text"
        }

    messages = [{"role": "system", "content": INDEX_GURU_SYSTEM_PROMPT}]

    if history and isinstance(history, list):
        for h in history[-6:]:  # last 6 exchanges
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=600
        )
        reply = response.choices[0].message.content.strip()
        return {
            "reply": reply,
            "mode": "intro"
        }
    except Exception as error:
        print("INDEX GURU CHAT ERROR:", error)
        # Fallback friendly response
        return {
            "reply": "Namaste! I am Guru, your AI guide. Bharat Study Buddy helps Indian students study smarter by turning PDFs, PPTs, and lecture videos into source-cited AI answers, adaptive quizzes, study timetables, and voice-assisted revision. Click 'Get Started' above to create your free account!",
            "mode": "fallback"
        }


# =========================================================
# DASHBOARD GURU: ADVANCED PERSONAL AI VOICE ASSISTANT
# =========================================================

DASHBOARD_GURU_SYSTEM_TEMPLATE = """You are Guru, the intelligent, encouraging, and highly competent Personal AI Study Teacher and Voice Assistant for {student_name} on Bharat Study Buddy.

You act as a live conversational tutor. Students speak to you or message you to plan their studies, solve difficult academic doubts, review smart notes, practice flashcards, and prepare for upcoming exams.

STUDENT PROFILE & CONTEXT:
- Student Name: {student_name}
- Email: {student_email}
- Uploaded Materials in Knowledge Base: {uploaded_sources_summary}
- Upcoming Examination Schedule:
{exam_schedule_summary}
- AI Study Planner Progress:
{study_plan_summary}

RELEVANT KNOWLEDGE RETRIEVED FROM STUDENT'S UPLOADED MATERIALS (RAG):
{rag_context}

YOUR CORE ABILITIES:
1. Continuous Voice Conversation: Respond naturally. Because your words may be read aloud, keep responses engaging, concise, and structured. When giving detailed technical explanations, use clear bullet points and bold key terms.
2. Multilingual Fluency: Understand and speak naturally in English, Hindi (हिंदी), and Hinglish (e.g. "Namaste! Aaj hum DBMS Normalization cover karenge"). Adapt seamlessly to the student's chosen language.
3. RAG Grounding: When answering conceptual questions, refer strictly to the retrieved study material and cite sources like [PDF Page X], [PPT Slide Y], or [Video Xs]. If information is not in their material, clearly state it and offer general educational guidance.
4. Exam Date Awareness: You know the student's upcoming exams and remaining days. Proactively remind them of approaching deadlines and suggest daily study targets based on remaining time.
5. Study Guidance: If the student asks "Guru, what should I study today?", look at their exam dates, study plan progress, weak topics, and uploaded notes to give a realistic, prioritized 3-step action plan.
6. Academic Tools: Offer to generate Smart Notes, Flashcards, or Practice Papers whenever the student needs revision.

VOICE GUIDELINES:
- Greet the student warmly by name.
- Avoid unnecessarily long filler phrases. Get straight to the helpful, accurate answer.
- If asked about modifying a saved study plan, confirm with the student first.
"""

def chat_dashboard_guru(user_id, user_message, history=None):
    """
    Main conversational brain for Dashboard Guru.
    Gathers student profile, exam dates, study plan, and RAG study material,
    then calls Groq LLM.
    """
    if not client:
        return {
            "reply": "Namaste! I am your AI study assistant Guru. Please ensure the backend GROQ_API_KEY is configured.",
            "sources": []
        }

    # 1. Gather student context
    student = get_student_info(user_id)
    student_name = student.get("name", "Student")
    student_email = student.get("email", "")

    # 2. Gather exam dates
    exam_dates = get_exam_dates(user_id)
    if exam_dates:
        exam_summary_lines = []
        for ed in exam_dates:
            days = ed.get("days_remaining")
            if days is not None and days >= 0:
                exam_summary_lines.append(f"- {ed['subject']}: {ed['exam_date']} ({days} days remaining)")
            elif days is not None and days < 0:
                exam_summary_lines.append(f"- {ed['subject']}: {ed['exam_date']} (Completed / Past)")
            else:
                exam_summary_lines.append(f"- {ed['subject']}: {ed['exam_date']}")
        exam_schedule_summary = "\n".join(exam_summary_lines)
    else:
        exam_schedule_summary = "No upcoming exam dates saved yet. (Student can tell you their exam dates to remember!)"

    # 3. Gather study planner status
    planner_status = get_study_plans_summary(user_id)
    plans = planner_status.get("plans", [])
    today_tasks = planner_status.get("today_tasks", [])

    if plans:
        plan_lines = []
        for p in plans:
            plan_lines.append(f"- Plan '{p['title']}': {p.get('progress_percent', 0)}% completed ({p.get('completed_tasks', 0)}/{p.get('total_tasks', 0)} tasks). Subjects: {p.get('subjects')}. Weak topics: {p.get('weak_subjects')}")
        if today_tasks:
            plan_lines.append(f"Tasks scheduled for today: {len(today_tasks)} tasks ({', '.join([t['topic'] for t in today_tasks[:3]])})")
        study_plan_summary = "\n".join(plan_lines)
    else:
        study_plan_summary = "No active AI study plan found. Student can generate one in the Study Planner."

    # 4. Check uploaded materials count
    kb = load_knowledge_base(user_id)
    pdf_count = len(kb.get("pdf", []))
    ppt_count = len(kb.get("ppt", []))
    video_count = len(kb.get("video", []))
    total_chunks = pdf_count + ppt_count + video_count
    uploaded_sources_summary = f"{total_chunks} total items processed ({pdf_count} PDF pages, {ppt_count} PPT slides, {video_count} video transcript segments)"

    # 5. RAG retrieval
    rag_sources = search_knowledge(user_message, top_k=6, user_id=user_id)
    rag_parts = []
    for s in rag_sources:
        citation = s.get("source", "MATERIAL")
        if citation == "PDF":
            citation += f" Page {s.get('page')}"
        elif citation == "PPT":
            citation += f" Slide {s.get('slide')}"
        elif citation == "VIDEO":
            citation += f" {s.get('start', 0)}s - {s.get('end', 0)}s"
        rag_parts.append(f"[{citation}]\n{s.get('text', '')}")

    rag_context = "\n\n".join(rag_parts) if rag_parts else "No direct keyword matches found in current uploaded materials for this specific query."

    # 6. Build system prompt
    system_prompt = DASHBOARD_GURU_SYSTEM_TEMPLATE.format(
        student_name=student_name,
        student_email=student_email,
        uploaded_sources_summary=uploaded_sources_summary,
        exam_schedule_summary=exam_schedule_summary,
        study_plan_summary=study_plan_summary,
        rag_context=rag_context
    )

    messages = [{"role": "system", "content": system_prompt}]

    if history and isinstance(history, list):
        for h in history[-8:]:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=850
        )
        reply = response.choices[0].message.content.strip()

        # Check if the user mentioned setting an exam date (e.g., "Mera DBMS exam 28 November ko hai")
        # We can extract and suggest saving the exam date if present
        date_save_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", user_message)

        return {
            "reply": reply,
            "sources": rag_sources,
            "student_name": student_name,
            "exam_dates": exam_dates
        }
    except Exception as error:
        print("DASHBOARD GURU ERROR:", error)
        return {
            "reply": f"Namaste {student_name}! I encountered a temporary connection issue with the AI engine. Please try asking again in a moment.",
            "sources": []
        }


# =========================================================
# PAPER ANALYZER INTEGRATION
# =========================================================

def analyze_student_papers(user_id, subject=None):
    """
    Analyzes uploaded study materials, syllabus guides, or previous exam papers
    for the student. Identifies repeated questions, exam patterns, and high-priority topics.
    """
    if not client:
        raise RuntimeError("Groq API client not initialized.")

    # Retrieve relevant exam/paper sections from knowledge base
    query = f"{subject or ''} examination question paper repeated questions important topics syllabus pattern weightage marks"
    materials = search_knowledge(query, top_k=15, user_id=user_id)

    if not materials:
        # Fallback to general knowledge base items
        kb = load_knowledge_base(user_id)
        all_texts = []
        for item in kb.get("pdf", [])[:10]:
            all_texts.append(f"[PDF Page {item.get('page')}] {item.get('text', '')}")
        context = "\n\n".join(all_texts)
    else:
        context = "\n\n".join([f"[{m.get('source')} Page/Slide {m.get('page', m.get('slide', '?'))}]\n{m.get('text', '')}" for m in materials])

    if not context.strip():
        return {
            "success": False,
            "message": "No study materials or question papers found. Please upload your syllabus or previous papers first."
        }

    prompt = f"""
You are Bharat Study Buddy's expert Academic Paper Analyzer.
Analyze the following study material and question papers for subject: {subject or 'All Subjects'}.

Identify:
1. High-frequency and repeated exam questions / concepts.
2. Important topics and estimated marks weightage.
3. Exam paper pattern insights (e.g. MCQ vs Short vs Long theory/numerical).
4. Recommended 3-tier revision priority (Tier 1: High yield must-study, Tier 2: Medium yield, Tier 3: Low yield revision).

Return ONLY valid JSON without markdown fences:
{{
  "subject": "{subject or 'Curriculum'}",
  "repeated_questions": [
    {{"question": "Repeated question or core concept", "frequency": "High/Medium", "importance": "Crucial for exams"}}
  ],
  "important_topics": [
    {{"topic": "Topic Name", "weightage": "Approx 15-20 Marks", "reason": "Frequently asked in Section B/C"}}
  ],
  "pattern_insights": [
    "Key observation about question paper structure or repeated patterns"
  ],
  "priority_revision_strategy": [
    {{"tier": "Tier 1 (High Yield)", "topics": ["Topic A", "Topic B"], "action": "Memorize definitions and practice diagrams"}}
  ]
}}

STUDY MATERIAL:
{context[:7000]}
"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    data = clean_json_response(response.choices[0].message.content)
    return {"success": True, "analysis": data}


# =========================================================
# SMART NOTES GENERATOR
# =========================================================

def generate_guru_smart_notes(user_id, topic=None):
    """
    Generates structured, unit-wise, bulleted smart notes grounded in student's uploaded materials.
    """
    if not client:
        raise RuntimeError("Groq API client not initialized.")

    query = f"{topic or 'important concepts definitions formulas explanations unit summary'}"
    sources = search_knowledge(query, top_k=15, user_id=user_id)

    if not sources:
        kb = load_knowledge_base(user_id)
        all_texts = []
        for item in kb.get("pdf", [])[:10]:
            all_texts.append(f"[PDF Page {item.get('page')}] {item.get('text', '')}")
        for item in kb.get("ppt", [])[:10]:
            all_texts.append(f"[PPT Slide {item.get('slide')}] {item.get('text', '')}")
        context = "\n\n".join(all_texts)
    else:
        context = "\n\n".join([f"[{s.get('source')} Page/Slide {s.get('page', s.get('slide', '?'))}]\n{s.get('text', '')}" for s in sources])

    if not context.strip():
        return {
            "success": False,
            "message": "No uploaded study materials found. Please upload notes or syllabus first."
        }

    prompt = f"""
You are Bharat Study Buddy's Smart Notes Generator.
Generate clear, comprehensive, and student-friendly revision notes for topic: {topic or 'Key Concepts'}.
Use ONLY the provided study material.
Return ONLY valid JSON without markdown fences:
{{
  "title": "Smart Notes: {topic or 'Curriculum Essentials'}",
  "topic": "{topic or 'Key Concepts'}",
  "sections": [
    {{
      "heading": "Section Heading",
      "definitions": ["Definition 1", "Definition 2"],
      "key_points": ["Key point with [Source citation]"],
      "formulas_or_rules": ["Important formula or principle if any"],
      "exam_tips": "Last-minute tip for exams"
    }}
  ]
}}

STUDY MATERIAL:
{context[:7000]}
"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    data = clean_json_response(response.choices[0].message.content)
    return {"success": True, "notes": data}


# =========================================================
# FLASHCARD GENERATOR
# =========================================================

def generate_guru_flashcards(user_id, topic=None):
    """
    Generates 6-8 interactive flashcards from uploaded study materials.
    """
    if not client:
        raise RuntimeError("Groq API client not initialized.")

    query = f"{topic or 'key definitions formulas differences core concepts'}"
    sources = search_knowledge(query, top_k=12, user_id=user_id)

    if not sources:
        kb = load_knowledge_base(user_id)
        all_texts = []
        for item in kb.get("pdf", [])[:10]:
            all_texts.append(f"[PDF Page {item.get('page')}] {item.get('text', '')}")
        for item in kb.get("ppt", [])[:10]:
            all_texts.append(f"[PPT Slide {item.get('slide')}] {item.get('text', '')}")
        context = "\n\n".join(all_texts)
    else:
        context = "\n\n".join([f"[{s.get('source')}]\n{s.get('text', '')}" for s in sources])

    if not context.strip():
        return {
            "success": False,
            "message": "No study materials found to create flashcards from. Please upload materials first."
        }

    prompt = f"""
Generate 6 to 8 flashcards for active recall study based ONLY on the study material below.
Format: Question on the front, clear and concise answer on the back.
Return ONLY valid JSON without markdown fences:
{{
  "topic": "{topic or 'Study Cards'}",
  "flashcards": [
    {{
      "id": 1,
      "category": "Definition / Formula / Concept / Comparison",
      "question": "Clear question or term to define",
      "answer": "Concise, accurate answer grounded in material",
      "source_reference": "Citation like [PDF Page X]"
    }}
  ]
}}

STUDY MATERIAL:
{context[:6000]}
"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    data = clean_json_response(response.choices[0].message.content)
    return {"success": True, "flashcards": data.get("flashcards", [])}


# =========================================================
# PRACTICE PAPER GENERATOR
# =========================================================

def generate_guru_practice_paper(user_id, subject=None, paper_type="mcq"):
    """
    Generates practice questions (MCQs or Short/Long answer questions)
    with model answers and marking criteria.
    """
    if not client:
        raise RuntimeError("Groq API client not initialized.")

    query = f"{subject or ''} important questions definitions numericals problems topics"
    sources = search_knowledge(query, top_k=15, user_id=user_id)

    if not sources:
        kb = load_knowledge_base(user_id)
        all_texts = []
        for item in kb.get("pdf", [])[:10]:
            all_texts.append(f"[PDF Page {item.get('page')}] {item.get('text', '')}")
        for item in kb.get("ppt", [])[:10]:
            all_texts.append(f"[PPT Slide {item.get('slide')}] {item.get('text', '')}")
        context = "\n\n".join(all_texts)
    else:
        context = "\n\n".join([f"[{s.get('source')}]\n{s.get('text', '')}" for s in sources])

    if not context.strip():
        return {
            "success": False,
            "message": "No study materials found for this subject. Please upload notes first."
        }

    prompt = f"""
Generate a realistic academic practice test paper for Indian students.
Subject: {subject or 'Curriculum'}
Test Type: {paper_type.upper()}
Use ONLY the provided material.
Return ONLY valid JSON without markdown fences.

Format for MCQ:
{{
  "title": "Practice Paper: {subject or 'Mock Test'}",
  "type": "MCQ",
  "questions": [
    {{
      "id": 1,
      "question": "Question text?",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "Why option 0 is correct",
      "marks": 2
    }}
  ]
}}

Format for Short/Long answers:
{{
  "title": "Practice Paper: {subject or 'Mock Test'}",
  "type": "THEORY",
  "questions": [
    {{
      "id": 1,
      "question": "Question text",
      "marks": 5,
      "model_answer": "Complete ideal student answer with key points and diagrams if relevant",
      "evaluation_criteria": ["Criteria 1", "Criteria 2"]
    }}
  ]
}}

STUDY MATERIAL:
{context[:6500]}
"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    data = clean_json_response(response.choices[0].message.content)
    return {"success": True, "paper": data}
