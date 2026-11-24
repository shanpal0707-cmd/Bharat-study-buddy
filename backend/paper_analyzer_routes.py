"""
Bharat Study Buddy — Paper Analyzer Routes Blueprint
===================================================
API routes mounted at /api/paper-analyzer:
- POST   /upload    Upload single or multiple previous year question papers
- GET    /papers    List uploaded papers
- DELETE /papers/<id> Remove a paper
- POST   /clear     Remove all papers
- POST   /analyze   Trigger AI semantic repetition & priority analysis
- GET    /report    Get latest analysis report
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import paper_analyzer_service as service

paper_analyzer_bp = Blueprint("paper_analyzer", __name__, url_prefix="/api/paper-analyzer")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function


@paper_analyzer_bp.route("/upload", methods=["POST"])
@login_required
def upload_papers():
    """
    Handles uploading one or multiple question papers with metadata.
    """
    user_id = session["user_id"]

    # Gather files
    files = request.files.getlist("files")
    if not files and "file" in request.files:
        files = [request.files["file"]]

    if not files or len(files) == 0:
        return jsonify({"success": False, "message": "No files selected for upload."}), 400

    subject = request.form.get("subject", "").strip()
    exam_name = request.form.get("exam_name", "").strip()
    year = request.form.get("year", "").strip()

    uploaded_results = []
    errors = []

    for f in files:
        if not f.filename:
            continue
        try:
            res = service.save_question_paper(
                user_id=user_id,
                file_storage=f,
                subject=subject,
                exam_name=exam_name,
                year=year
            )
            uploaded_results.append(res)
        except Exception as e:
            errors.append(f"{f.filename}: {str(e)}")

    if not uploaded_results and errors:
        return jsonify({
            "success": False,
            "message": "Upload failed for all files.",
            "errors": errors
        }), 400

    return jsonify({
        "success": True,
        "uploaded_count": len(uploaded_results),
        "uploaded_papers": uploaded_results,
        "errors": errors
    })


@paper_analyzer_bp.route("/papers", methods=["GET"])
@login_required
def get_papers():
    """
    Lists all uploaded question papers for the student.
    """
    user_id = session["user_id"]
    try:
        papers = service.list_user_question_papers(user_id)
        return jsonify({
            "success": True,
            "count": len(papers),
            "papers": papers
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@paper_analyzer_bp.route("/papers/<int:paper_id>", methods=["DELETE"])
@login_required
def delete_paper(paper_id):
    """
    Deletes a specific question paper.
    """
    user_id = session["user_id"]
    try:
        ok = service.delete_user_question_paper(user_id, paper_id)
        if ok:
            return jsonify({"success": True, "message": "Paper removed successfully."})
        return jsonify({"success": False, "message": "Paper not found or already deleted."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@paper_analyzer_bp.route("/clear", methods=["POST"])
@login_required
def clear_all():
    """
    Removes all uploaded question papers and reports for the student.
    """
    user_id = session["user_id"]
    try:
        service.clear_all_user_papers(user_id)
        return jsonify({"success": True, "message": "All question papers cleared."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@paper_analyzer_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_papers():
    """
    Runs full AI analysis on the uploaded papers.
    """
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    subject_filter = data.get("subject")

    try:
        report = service.run_paper_analysis(user_id, subject_filter=subject_filter)
        return jsonify({
            "success": True,
            "report": report
        })
    except ValueError as ve:
        err_msg = str(ve)
        # Check if this is a user input validation error
        if "No uploaded question papers" in err_msg:
            return jsonify({"success": False, "message": err_msg}), 400
        # If it's an AI output parsing error, return a meaningful error
        return jsonify({
            "success": False,
            "message": "AI analysis could not complete due to an unexpected format from the AI provider. Please try again."
        }), 502
    except Exception as e:
        print("Paper Analyzer error:", e)
        return jsonify({
            "success": False,
            "message": f"Analysis failed: {str(e)}"
        }), 500


@paper_analyzer_bp.route("/report", methods=["GET"])
@login_required
def get_report():
    """
    Retrieves the most recent paper analyzer report.
    """
    user_id = session["user_id"]
    try:
        report = service.get_latest_report(user_id)
        if report:
            return jsonify({
                "success": True,
                "has_report": True,
                "report": report
            })
        return jsonify({
            "success": True,
            "has_report": False,
            "message": "No previous analysis report found. Please upload papers and run analysis."
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
