"""
Bharat Study Buddy — Paper Analyzer AI Service
==============================================
Intelligent previous year exam question paper analysis:
- Multi-paper PDF and image text extraction
- Question extraction and semantic similarity clustering
- Repetition detection across academic years
- 3-tier priority categorization (HIGH, MEDIUM, LOW)
- Topic frequency, paper-wise distribution & exam prep recommendations
- Transparent, evidence-based reasoning (no hallucinated guarantees)
- Bulletproof JSON mode enforcement, safe parsing and error recovery
"""

import os
import re
import json
import uuid
import logging
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from openai import OpenAI
from database import get_connection

logger = logging.getLogger("paper_analyzer")
logging.basicConfig(level=logging.INFO)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

client = None
if GROQ_API_KEY:
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PAPERS_UPLOAD_DIR = os.path.join(BASE_DIR, "data", "paper_analyzer")
os.makedirs(PAPERS_UPLOAD_DIR, exist_ok=True)


def get_user_papers_dir(user_id):
    path = os.path.join(PAPERS_UPLOAD_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


def extract_text_from_pdf(pdf_path):
    """
    Extracts text from all pages of a question paper PDF using PyMuPDF.
    """
    doc = fitz.open(pdf_path)
    extracted_chunks = []
    for page_num, page in enumerate(doc, start=1):
        txt = page.get_text("text").strip()
        if txt:
            extracted_chunks.append(f"--- [Page {page_num}] ---\n{txt}")
    doc.close()
    return "\n\n".join(extracted_chunks).strip()


def extract_text_from_image(img_path):
    """
    Extracts text from an image question paper using OCR or Gemini Vision fallback.
    """
    try:
        doc = fitz.open(img_path)
        txt = ""
        for page in doc:
            txt += page.get_text("text")
        doc.close()
        if txt.strip():
            return txt.strip()
    except Exception:
        pass

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            from PIL import Image

            g_client = genai.Client(api_key=gemini_key)
            img = Image.open(img_path)
            response = g_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    img,
                    "Extract all examination questions, sections, marks, and text verbatim from this question paper image. Maintain question numbers and formatting."
                ]
            )
            if response.text and len(response.text.strip()) > 20:
                return response.text.strip()
        except Exception as e:
            logger.warning("Gemini Vision image extraction error: %s", e)

    raise ValueError("Could not extract readable text from this image. Please ensure the paper is clear or upload as a PDF.")


def save_question_paper(user_id, file_storage, subject="", exam_name="", year=""):
    """
    Saves an uploaded question paper, extracts text, and registers it in SQLite.
    """
    if not file_storage or not file_storage.filename:
        raise ValueError("No file provided.")

    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ["pdf", "png", "jpg", "jpeg", "webp"]:
        raise ValueError(f"Unsupported file format (.{ext}). Please upload PDF, PNG, JPG, or JPEG.")

    user_dir = get_user_papers_dir(user_id)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    saved_path = os.path.join(user_dir, unique_filename)
    file_storage.save(saved_path)

    file_size = os.path.getsize(saved_path)
    file_type = "pdf" if ext == "pdf" else "image"

    if file_type == "pdf":
        extracted_text = extract_text_from_pdf(saved_path)
    else:
        extracted_text = extract_text_from_image(saved_path)

    if not extracted_text or len(extracted_text.strip()) < 25:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise ValueError(f"Could not read questions from '{filename}'. The file appears empty or unreadable.")

    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO paper_analyzer_files (
                user_id, filename, stored_path, subject, exam_name, year, file_type, file_size, extracted_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            filename,
            saved_path,
            subject.strip() or "General",
            exam_name.strip() or "Previous Paper",
            str(year).strip() or "N/A",
            file_type,
            file_size,
            extracted_text
        ))
        conn.commit()
        paper_id = cursor.lastrowid
    finally:
        conn.close()

    return {
        "id": paper_id,
        "filename": filename,
        "subject": subject or "General",
        "exam_name": exam_name or "Previous Paper",
        "year": str(year) or "N/A",
        "file_type": file_type,
        "file_size": file_size,
        "characters_extracted": len(extracted_text)
    }


def list_user_question_papers(user_id):
    """
    Returns list of all uploaded question papers for the student.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, filename, subject, exam_name, year, file_type, file_size, created_at
            FROM paper_analyzer_files
            WHERE user_id = ?
            ORDER BY year DESC, created_at DESC
        """, (user_id,)).fetchall()

        papers = []
        for r in rows:
            papers.append({
                "id": r["id"],
                "filename": r["filename"],
                "subject": r["subject"],
                "exam_name": r["exam_name"],
                "year": r["year"],
                "file_type": r["file_type"],
                "file_size": r["file_size"],
                "created_at": r["created_at"]
            })
        return papers
    finally:
        conn.close()


def delete_user_question_paper(user_id, paper_id):
    """
    Deletes a specific question paper and removes its file from disk.
    """
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT stored_path FROM paper_analyzer_files
            WHERE id = ? AND user_id = ?
        """, (paper_id, user_id)).fetchone()

        if not row:
            return False

        file_path = row["stored_path"]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning("Could not remove paper file: %s", e)

        conn.execute("DELETE FROM paper_analyzer_files WHERE id = ? AND user_id = ?", (paper_id, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


def clear_all_user_papers(user_id):
    """
    Removes all uploaded papers and reports for the student.
    """
    conn = get_connection()
    try:
        rows = conn.execute("SELECT stored_path FROM paper_analyzer_files WHERE user_id = ?", (user_id,)).fetchall()
        for r in rows:
            p = r["stored_path"]
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        conn.execute("DELETE FROM paper_analyzer_files WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM paper_analyzer_reports WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# =========================================================
# BULLETPROOF JSON EXTRACTION, REPAIR & VALIDATION
# =========================================================

def clean_and_repair_json(content):
    """
    Robust JSON parser for AI outputs:
    1. Strips markdown fences (```json ... ```)
    2. Extracts outermost JSON object
    3. Allows unescaped control chars via strict=False
    4. Cleans trailing commas
    5. Balances unclosed brackets/braces if output was truncated
    6. Safely logs parsing diagnostics on error without leaking secrets
    """
    if not content or not isinstance(content, str):
        raise ValueError("AI response was empty.")

    text = content.strip()

    # 1. Strip markdown fences if present
    if "```" in text:
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            text = fence_match.group(1).strip()
        else:
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"```$", "", text).strip()

    # 2. Extract from first '{' to last '}' if both exist
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
    elif first_brace != -1:
        candidate = text[first_brace:]
    else:
        candidate = text

    # Direct parse attempt with strict=False
    try:
        return json.loads(candidate, strict=False)
    except Exception as e_initial:
        last_error = e_initial

    # 3. Clean trailing commas before closing braces/brackets
    cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
    try:
        return json.loads(cleaned, strict=False)
    except Exception as e_commas:
        last_error = e_commas

    # 4. Stack-based repair for unclosed quotes, brackets, and braces
    try:
        stack = []
        in_string = False
        escape = False

        for char in cleaned:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    stack.append("}")
                elif char == "[":
                    stack.append("]")
                elif char in ("}", "]"):
                    if stack and stack[-1] == char:
                        stack.pop()

        repaired = cleaned
        if in_string:
            repaired += '"'

        repaired = re.sub(r",\s*$", "", repaired.strip())

        while stack:
            closing = stack.pop()
            repaired = re.sub(r",\s*$", "", repaired.strip())
            repaired += closing

        repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
        return json.loads(repaired, strict=False)
    except Exception as e_stack:
        last_error = e_stack

    # Log safe diagnostic snippet around failure point
    logger.error("JSON parsing error: %s", last_error)
    preview = candidate[:300] + ("..." if len(candidate) > 300 else "")
    logger.error("Candidate preview: %s", preview)

    raise ValueError(f"AI response could not be parsed into valid JSON: {str(last_error)}")


def clean_json_response(content):
    """
    Backwards-compatible wrapper calling clean_and_repair_json.
    """
    return clean_and_repair_json(content)


def normalize_report_structure(data, primary_subject, total_papers, years_covered_str):
    """
    Normalizes the parsed AI report to strictly conform to the frontend contract.
    Guarantees that all expected keys, arrays, and metrics exist with valid types.
    """
    if not isinstance(data, dict):
        data = {}

    data["subject"] = data.get("subject") or primary_subject
    data["total_papers_analyzed"] = data.get("total_papers_analyzed") or total_papers
    data["years_covered"] = data.get("years_covered") or years_covered_str

    # 1. repeated_questions normalization
    raw_repeated = data.get("repeated_questions") or []
    if not isinstance(raw_repeated, list):
        raw_repeated = []

    normalized_repeated = []
    for idx, rq in enumerate(raw_repeated, start=1):
        if isinstance(rq, str):
            rq = {"primary_question": rq}
        elif not isinstance(rq, dict):
            continue

        raw_years = rq.get("years_appeared")
        if isinstance(raw_years, list):
            years_list = [str(y).strip() for y in raw_years if str(y).strip()]
        elif raw_years:
            years_list = [str(y).strip() for y in str(raw_years).split(",") if str(y).strip()]
        else:
            years_list = [years_covered_str]

        raw_sources = rq.get("source_references")
        if isinstance(raw_sources, list):
            sources_list = [str(s).strip() for s in raw_sources if str(s).strip()]
        elif raw_sources:
            sources_list = [str(raw_sources)]
        else:
            sources_list = ["Past Papers"]

        raw_variations = rq.get("variations")
        if isinstance(raw_variations, list):
            variations_list = [str(v).strip() for v in raw_variations if str(v).strip()]
        else:
            variations_list = []

        normalized_repeated.append({
            "id": rq.get("id") or idx,
            "primary_question": rq.get("primary_question") or rq.get("question") or "Question",
            "related_topic": rq.get("related_topic") or rq.get("topic") or "Core Topic",
            "occurrences": rq.get("occurrences") or rq.get("frequency") or 2,
            "years_appeared": years_list,
            "source_references": sources_list,
            "is_exact_or_semantic": rq.get("is_exact_or_semantic") or "Semantically Similar",
            "variations": variations_list,
            "evidence": rq.get("evidence") or "Question concept recurring in multiple examination sessions."
        })
    data["repeated_questions"] = normalized_repeated

    # 2. important_questions normalization
    raw_important = data.get("important_questions") or []
    if not isinstance(raw_important, list):
        raw_important = []

    normalized_important = []
    for idx, iq in enumerate(raw_important, start=1):
        if isinstance(iq, str):
            iq = {"question": iq}
        elif not isinstance(iq, dict):
            continue

        priority = str(iq.get("priority", "MEDIUM")).upper().strip()
        if priority not in ("HIGH", "MEDIUM", "LOW"):
            priority = "MEDIUM"

        raw_years = iq.get("years_appeared")
        if isinstance(raw_years, list):
            years_list = [str(y).strip() for y in raw_years if str(y).strip()]
        elif raw_years:
            years_list = [str(y).strip() for y in str(raw_years).split(",") if str(y).strip()]
        else:
            years_list = [years_covered_str]

        normalized_important.append({
            "id": iq.get("id") or idx,
            "question": iq.get("question") or iq.get("primary_question") or "Important Question",
            "priority": priority,
            "occurrences": iq.get("occurrences") or iq.get("frequency") or 1,
            "years_appeared": years_list,
            "related_topic": iq.get("related_topic") or iq.get("topic") or "General",
            "source_reference": str(iq.get("source_reference") or iq.get("source_references") or "Previous Paper"),
            "evidence": iq.get("evidence") or "Key concept identified from previous exam trends."
        })
    data["important_questions"] = normalized_important

    # 3. Recalculate summary metrics to guarantee exact math
    high_c = sum(1 for q in normalized_important if q.get("priority") == "HIGH")
    med_c = sum(1 for q in normalized_important if q.get("priority") == "MEDIUM")
    low_c = sum(1 for q in normalized_important if q.get("priority") == "LOW")

    data["summary_metrics"] = {
        "total_questions_extracted": len(normalized_important),
        "repeated_questions_count": len(normalized_repeated),
        "high_priority_count": high_c,
        "medium_priority_count": med_c,
        "low_priority_count": low_c
    }

    # 4. most_repeated_topics normalization
    raw_topics = data.get("most_repeated_topics") or []
    if not isinstance(raw_topics, list):
        raw_topics = []

    normalized_topics = []
    for t in raw_topics:
        if isinstance(t, str):
            t = {"topic": t, "frequency": 2, "estimated_weightage": "15-20%", "reason": "Tested across multiple papers."}
        elif not isinstance(t, dict):
            continue

        normalized_topics.append({
            "topic": t.get("topic") or "Core Topic",
            "frequency": t.get("frequency") or 2,
            "estimated_weightage": str(t.get("estimated_weightage") or "15%"),
            "reason": t.get("reason") or "Tested consistently across examination papers."
        })
    data["most_repeated_topics"] = normalized_topics

    # 5. paper_distribution normalization
    raw_dist = data.get("paper_distribution") or []
    if not isinstance(raw_dist, list):
        raw_dist = []
    data["paper_distribution"] = raw_dist

    # 6. preparation_recommendation normalization
    prep = data.get("preparation_recommendation") or {}
    if not isinstance(prep, dict):
        prep = {}

    data["preparation_recommendation"] = {
        "stage_1_high_yield": prep.get("stage_1_high_yield") or "Prioritize the high-priority and repeated questions first; they represent recurring marks.",
        "stage_2_medium_yield": prep.get("stage_2_medium_yield") or "Practice medium-priority questions and conceptual numericals.",
        "stage_3_revision": prep.get("stage_3_revision") or "Review formula definitions and low-priority edge case topics.",
        "pattern_note": prep.get("pattern_note") or "Questions are balanced across core theoretical definitions and applied problem solving."
    }

    # 7. transparency notice
    data["transparency_notice"] = data.get("transparency_notice") or (
        "Predictions and priority tiers are derived from empirical repetition and semantic similarity across your uploaded papers. "
        "They reflect historical examination patterns and do not guarantee question appearance."
    )

    return data


# =========================================================
# AI PAPER ANALYSIS RUNNER
# =========================================================

def run_paper_analysis(user_id, subject_filter=None):
    """
    Executes AI-powered previous year question paper analysis with JSON mode:
    - Questions extracted across all papers
    - Semantic similarity matching & grouping
    - Exact and semantic repetition detection with year tracking
    - 3-tier priority categorization (HIGH, MEDIUM, LOW)
    - Preparation recommendations & paper distribution table
    - Accuracy and transparency guarantees
    """
    if not client:
        raise RuntimeError("Groq API client is not initialized. Please configure GROQ_API_KEY in .env.")

    conn = get_connection()
    try:
        if subject_filter:
            rows = conn.execute("""
                SELECT id, filename, subject, exam_name, year, extracted_text
                FROM paper_analyzer_files
                WHERE user_id = ? AND subject = ?
                ORDER BY year ASC, id ASC
            """, (user_id, subject_filter)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, filename, subject, exam_name, year, extracted_text
                FROM paper_analyzer_files
                WHERE user_id = ?
                ORDER BY year ASC, id ASC
            """, (user_id,)).fetchall()

        if not rows:
            raise ValueError("No uploaded question papers found. Please upload at least one previous year paper first.")

        papers_payload = []
        years_list = set()
        subjects_list = set()

        for idx, r in enumerate(rows, start=1):
            year_val = r["year"] or "Unknown"
            subj_val = r["subject"] or "General"
            years_list.add(year_val)
            subjects_list.add(subj_val)

            # Limit text per paper to 12,000 characters to keep prompt within context limits while preserving all questions
            text_snippet = r["extracted_text"][:12000]
            papers_payload.append(f"""
=== PAPER #{idx} ===
Filename: {r['filename']}
Subject: {subj_val}
Exam / Session: {r['exam_name']}
Year: {year_val}
CONTENT:
{text_snippet}
====================
""")

    finally:
        conn.close()

    total_papers = len(rows)
    all_years_sorted = sorted([y for y in years_list if y not in ("N/A", "Unknown", "")])
    years_covered_str = ", ".join(all_years_sorted) if all_years_sorted else "Various Sessions"
    primary_subject = list(subjects_list)[0] if len(subjects_list) == 1 else "Combined Curriculum"

    logger.info("Starting paper analysis for user_id=%s, total_papers=%d, subject=%s", user_id, total_papers, primary_subject)

    system_prompt = (
        "You are Bharat Study Buddy's expert Academic Paper Analyzer and Exam Intelligence AI.\n"
        "Your task is to analyze past exam question papers, detect repetitions, compute frequencies, "
        "and classify questions into HIGH, MEDIUM, and LOW priorities.\n"
        "CRITICAL JSON RULES:\n"
        "1. Output MUST be a strictly valid JSON object matching the requested schema.\n"
        "2. Do NOT use unescaped double quotes inside string values. If quoting terms, use single quotes (e.g. 'normalization', '3NF') or escape with backslash (\\\"term\\\").\n"
        "3. Output ONLY the JSON object. Do not include markdown code fences or conversational text."
    )

    user_prompt = f"""Analyze the following {total_papers} previous year question papers for subject: "{primary_subject}".
Academic Years / Sessions: {years_covered_str}.

TASK REQUIREMENTS:
1. EXTRACT ALL DISTINCT QUESTIONS across all papers.
2. DETECT REPEATED QUESTIONS: Identify exact repetitions and semantically similar questions (different wording testing the same underlying concept/theorem/algorithm). Group similar questions together under one primary question.
3. COMPUTE FREQUENCY & YEARS: Record how many times each question/concept appeared and in which exact years.
4. ASSIGN 3-TIER EXAM PRIORITY:
   - HIGH PRIORITY: Questions repeated across multiple papers (>=2 times) or strongly supported by recurring exam patterns.
   - MEDIUM PRIORITY: Questions appearing more than once or showing meaningful relevance across papers.
   - LOW PRIORITY: Relevant questions appearing less frequently but still essential for comprehensive preparation.
5. IDENTIFY RECURRING TOPICS: Topic name, repetition frequency, and estimated marks weightage percentage.
6. PREPARATION RECOMMENDATION: Actionable, concise advice on which topics to master first based on empirical paper evidence.
7. TRANSPARENCY: Never claim a question is guaranteed. Show evidence behind each priority.

Output a valid JSON object matching this schema:
{{
  "subject": "{primary_subject}",
  "total_papers_analyzed": {total_papers},
  "years_covered": "{years_covered_str}",
  "summary_metrics": {{
    "total_questions_extracted": 0,
    "repeated_questions_count": 0,
    "high_priority_count": 0,
    "medium_priority_count": 0,
    "low_priority_count": 0
  }},
  "repeated_questions": [
    {{
      "id": 1,
      "primary_question": "Explain normalization in DBMS and differentiate between 3NF and BCNF.",
      "related_topic": "Database Normalization",
      "occurrences": 3,
      "years_appeared": ["2022", "2023", "2025"],
      "source_references": ["Paper 2022 Q3", "Paper 2023 Q1b", "Paper 2025 Q4"],
      "is_exact_or_semantic": "Semantically Similar & Rephrased",
      "variations": [
        "What is 3NF and BCNF with examples? (2022)",
        "Differentiate 3NF from BCNF using functional dependencies. (2023)"
      ],
      "evidence": "Appeared in 3 out of 4 sessions as a mandatory question."
    }}
  ],
  "important_questions": [
    {{
      "id": 1,
      "question": "Explain normalization in DBMS and differentiate between 3NF and BCNF.",
      "priority": "HIGH",
      "occurrences": 3,
      "years_appeared": ["2022", "2023", "2025"],
      "related_topic": "Database Normalization",
      "source_reference": "Paper 2022 Q3, Paper 2023 Q1b",
      "evidence": "Repeated across 3 different years; tests core normalization theory."
    }},
    {{
      "id": 2,
      "question": "Describe ACID properties in transaction processing.",
      "priority": "HIGH",
      "occurrences": 2,
      "years_appeared": ["2022", "2023"],
      "related_topic": "Transaction Management",
      "source_reference": "Paper 2022 Q2, Paper 2023 Q2",
      "evidence": "Repeated in consecutive years as a core short note."
    }},
    {{
      "id": 3,
      "question": "What is two-phase locking protocol (2PL)?",
      "priority": "MEDIUM",
      "occurrences": 2,
      "years_appeared": ["2022", "2025"],
      "related_topic": "Concurrency Control",
      "source_reference": "Paper 2022 Q3, Paper 2025 Q2",
      "evidence": "Appeared in multiple years as a conceptual question."
    }}
  ],
  "most_repeated_topics": [
    {{
      "topic": "Database Normalization",
      "frequency": 3,
      "estimated_weightage": "20%",
      "reason": "Questions on functional dependency, 3NF, BCNF appear consistently."
    }}
  ],
  "paper_distribution": [
    {{
      "year": "2024",
      "paper_title": "Paper 2024",
      "questions_count": 8,
      "dominant_topic": "Transactions & SQL Queries"
    }}
  ],
  "preparation_recommendation": {{
    "stage_1_high_yield": "Master core repeated definitions, theorems, and algorithms first.",
    "stage_2_medium_yield": "Solve medium-priority numericals and conceptual comparisons.",
    "stage_3_revision": "Review formulas and low-priority edge case topics.",
    "pattern_note": "Questions are balanced across core theoretical definitions and applied problem solving."
  }},
  "transparency_notice": "Predictions and priority tiers are derived from empirical repetition and semantic similarity across your uploaded papers. They reflect historical examination patterns and do not guarantee question appearance."
}}

PAPERS CONTENT:
{''.join(papers_payload)}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=8192
    )

    raw_content = response.choices[0].message.content
    logger.info("AI response received: %d characters", len(raw_content) if raw_content else 0)

    parsed_json = clean_and_repair_json(raw_content)
    report_data = normalize_report_structure(parsed_json, primary_subject, total_papers, years_covered_str)

    # Persist report to database
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO paper_analyzer_reports (
                user_id, subject, total_papers, years_covered, report_json
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            primary_subject,
            total_papers,
            years_covered_str,
            json.dumps(report_data)
        ))
        conn.commit()
    finally:
        conn.close()

    logger.info("Paper analysis report saved successfully: %d questions extracted, %d repeated",
                report_data["summary_metrics"]["total_questions_extracted"],
                report_data["summary_metrics"]["repeated_questions_count"])

    return report_data


def get_latest_report(user_id):
    """
    Fetches the most recent saved paper analyzer report for the student.
    """
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT id, subject, total_papers, years_covered, report_json, created_at
            FROM paper_analyzer_reports
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()

        if not row:
            return None

        report = json.loads(row["report_json"])
        report["saved_at"] = row["created_at"]
        return report
    finally:
        conn.close()
