import os
import sqlite3
from functools import wraps
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DB_PATH = BASE_DIR / "studymate.db"

# Load the .env file from the same folder as app.py, even if the terminal
# was opened from a different directory. override=True helps if the terminal
# already has an empty GROQ_API_KEY variable.
load_dotenv(ENV_PATH, override=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "studymate-dev-secret-change-this")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def get_db_connection():
    """Open a SQLite connection and return rows like dictionaries."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create the users table the first time the project runs."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def current_user():
    """Return the logged-in user record, or None if there is no session."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    with get_db_connection() as connection:
        return connection.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def login_required(view_function):
    """Protect pages and API routes from users who are not logged in."""
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Please log in first."}), 401
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapper


init_db()


def read_uploaded_file(uploaded_file):
    """Read a plain-text uploaded notes file in a beginner-friendly way."""
    if not uploaded_file or uploaded_file.filename == "":
        return ""

    filename = uploaded_file.filename.lower()
    if not filename.endswith((".txt", ".md")):
        raise ValueError("Please upload a .txt or .md notes file.")

    return uploaded_file.read().decode("utf-8", errors="ignore")


def get_notes_from_request():
    """Support both JSON requests and form-data requests with an uploaded file."""
    if request.is_json:
        data = request.get_json() or {}
        return (data.get("notes") or "").strip()

    pasted_notes = (request.form.get("notes") or "").strip()
    file_notes = read_uploaded_file(request.files.get("notes_file")).strip()
    return "\n\n".join(part for part in [pasted_notes, file_notes] if part)


def call_groq(system_prompt, user_prompt, max_tokens=900):
    """Send a prompt to Groq and return the AI response text."""
    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(f"GROQ_API_KEY is missing. Add it to {ENV_PATH}.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=35)
    response.raise_for_status()

    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def build_error_response(error):
    """Return simple JSON errors the frontend can show inside the app."""
    message = str(error)
    status_code = 500

    if isinstance(error, ValueError):
        status_code = 400
    elif isinstance(error, requests.exceptions.HTTPError):
        groq_status_code = error.response.status_code
        if groq_status_code == 401:
            message = "Groq API key is invalid or missing permission."
        elif groq_status_code == 429:
            message = "Groq rate limit reached. Please wait and try again."
        else:
            message = "Groq API request failed. Check your API key and try again."
    elif isinstance(error, requests.exceptions.RequestException):
        message = "Could not connect to Groq. Check your internet connection."

    return jsonify({"success": False, "error": message}), status_code


@app.route("/")
@login_required
def home():
    return render_template("index.html", user=current_user())


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("home"))

    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "Please fill in all fields."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            try:
                with get_db_connection() as connection:
                    cursor = connection.execute(
                        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                        (name, email, generate_password_hash(password)),
                    )
                    session["user_id"] = cursor.lastrowid
                    session["user_name"] = name
                    return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                error = "An account with this email already exists."

    return render_template("auth.html", mode="signup", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db_connection() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))

        error = "Invalid email or password."

    return render_template("auth.html", mode="login", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/summarize", methods=["POST"])
@login_required
def summarize_notes():
    try:
        notes = get_notes_from_request()
        if not notes:
            return jsonify({"success": False, "error": "Please add notes first."}), 400

        # The prompt asks Groq to return structured text that looks good in the result cards.
        system_prompt = (
            "You are a helpful study assistant for college students. "
            "Create clear, exam-friendly summaries using simple language."
        )
        user_prompt = f"""
Summarize these study notes.

Format your answer with:
- A short overview
- Key points
- Important terms
- 3 quick revision bullets

Notes:
{notes}
"""
        summary = call_groq(system_prompt, user_prompt)
        return jsonify({"success": True, "summary": summary})
    except Exception as error:
        return build_error_response(error)


@app.route("/api/quiz", methods=["POST"])
@login_required
def generate_quiz():
    try:
        notes = get_notes_from_request()
        if not notes:
            return jsonify({"success": False, "error": "Please add notes first."}), 400

        # Keeping the quiz format predictable makes the frontend simple for beginners.
        system_prompt = (
            "You create beginner-to-intermediate quiz questions from study notes. "
            "Keep questions accurate and useful for revision."
        )
        user_prompt = f"""
Create a quiz from these notes.

Return:
- 5 multiple-choice questions with 4 options each
- Mark the correct answer after each question
- Add a one-line explanation for each answer

Notes:
{notes}
"""
        quiz = call_groq(system_prompt, user_prompt)
        return jsonify({"success": True, "quiz": quiz})
    except Exception as error:
        return build_error_response(error)


@app.route("/api/ask", methods=["POST"])
@login_required
def ask_ai():
    try:
        notes = get_notes_from_request()
        if request.is_json:
            data = request.get_json() or {}
            question = (data.get("question") or "").strip()
        else:
            question = (request.form.get("question") or "").strip()

        if not notes:
            return jsonify({"success": False, "error": "Please add notes first."}), 400
        if not question:
            return jsonify({"success": False, "error": "Please type a question."}), 400

        # The notes are included with the question so answers stay connected to the user's material.
        system_prompt = (
            "You answer student doubts using the provided notes as the main source. "
            "If the answer is not in the notes, say so and give a careful general explanation."
        )
        user_prompt = f"""
Study notes:
{notes}

Student question:
{question}

Answer in a friendly, clear way. Use examples if helpful.
"""
        answer = call_groq(system_prompt, user_prompt)
        return jsonify({"success": True, "answer": answer})
    except Exception as error:
        return build_error_response(error)


@app.route("/api/flashcards", methods=["POST"])
@login_required
def generate_flashcards():
    try:
        notes = get_notes_from_request()
        if not notes:
            return jsonify({"success": False, "error": "Please add notes first."}), 400

        system_prompt = (
            "You create short flashcards for college students. "
            "Keep each answer clear enough for quick revision."
        )
        user_prompt = f"""
Create 8 flashcards from these notes.

Format each flashcard as:
Q: question
A: answer

Notes:
{notes}
"""
        flashcards = call_groq(system_prompt, user_prompt, max_tokens=850)
        return jsonify({"success": True, "flashcards": flashcards})
    except Exception as error:
        return build_error_response(error)


@app.route("/api/study-plan", methods=["POST"])
@login_required
def generate_study_plan():
    try:
        notes = get_notes_from_request()
        if not notes:
            return jsonify({"success": False, "error": "Please add notes first."}), 400

        system_prompt = (
            "You help students convert notes into a practical study plan. "
            "Make the plan specific, realistic, and easy to follow."
        )
        user_prompt = f"""
Create a 3-day study plan from these notes.

Include:
- Daily focus goal
- What to revise
- Practice task
- Quick self-check question

Notes:
{notes}
"""
        study_plan = call_groq(system_prompt, user_prompt, max_tokens=900)
        return jsonify({"success": True, "study_plan": study_plan})
    except Exception as error:
        return build_error_response(error)


@app.route("/api/health")
def health_check():
    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    return jsonify(
        {
            "success": True,
            "message": "Study Assistant backend is running.",
            "env_file_found": ENV_PATH.exists(),
            "env_file_path": str(ENV_PATH),
            "groq_key_loaded": bool(api_key),
            "model": GROQ_MODEL,
            "database_found": DB_PATH.exists(),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
