"""
AI-Powered Smart Interview Assistant
=====================================
Main Flask application entry point.
Handles routing, authentication, interview logic, and API endpoints.
"""

import os
import json
import random
import sqlite3
import base64
import re
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ── App Configuration ──────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "interview-assistant-secret-2024")
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
app.config["DATABASE"] = os.path.join("instance", "interview.db")

ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("instance", exist_ok=True)

# ── Database Helpers ───────────────────────────────────────────────────────────

def get_db():
    """Return a database connection, creating one if needed for this request."""
    if "db" not in g:
        g.db = sqlite3.connect(
            app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """Close the database connection at the end of each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all required tables if they don't already exist."""
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS interviews (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            job_role        TEXT    NOT NULL,
            difficulty      TEXT    NOT NULL,
            total_questions INTEGER DEFAULT 0,
            score           REAL    DEFAULT 0,
            emotion_score   REAL    DEFAULT 0,
            confidence_avg  REAL    DEFAULT 0,
            duration_sec    INTEGER DEFAULT 0,
            resume_used     INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS answers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id    INTEGER NOT NULL,
            question        TEXT    NOT NULL,
            answer          TEXT,
            score           REAL    DEFAULT 0,
            emotion         TEXT    DEFAULT 'neutral',
            confidence      REAL    DEFAULT 0,
            keywords_hit    INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            filename    TEXT    NOT NULL,
            content     TEXT,
            skills      TEXT,
            uploaded_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()


# ── Auth Helpers ───────────────────────────────────────────────────────────────

def login_required(f):
    """Decorator: redirect to login page if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Question Bank ──────────────────────────────────────────────────────────────

QUESTION_BANK = {
    "Software Engineer": {
        "easy": [
            "Tell me about yourself and your programming background.",
            "What programming languages are you most comfortable with?",
            "Explain the difference between a list and a tuple in Python.",
            "What is Object-Oriented Programming?",
            "What is version control and why is it important?",
            "Describe what an API is in simple terms.",
            "What is the difference between frontend and backend development?",
            "How do you debug code when something goes wrong?",
        ],
        "medium": [
            "Explain the SOLID principles in software design.",
            "What is the difference between SQL and NoSQL databases?",
            "How do you approach optimizing a slow database query?",
            "Explain the concept of RESTful APIs.",
            "What is the difference between synchronous and asynchronous programming?",
            "Describe how you would implement a caching strategy.",
            "What are design patterns and can you name a few?",
            "How do you ensure code quality in a team environment?",
        ],
        "hard": [
            "Design a URL shortening service like bit.ly. Walk me through your architecture.",
            "Explain CAP theorem and how it applies to distributed systems.",
            "How would you implement a real-time chat application at scale?",
            "What is eventual consistency and when would you choose it?",
            "Describe how garbage collection works in modern programming languages.",
            "How would you design a rate limiter for an API?",
            "Explain the concept of microservices vs monolithic architecture.",
            "How do you handle database migrations in a production environment?",
        ],
    },
    "Data Scientist": {
        "easy": [
            "What is the difference between supervised and unsupervised learning?",
            "Explain what overfitting means and how to prevent it.",
            "What is a confusion matrix?",
            "What Python libraries do you use for data analysis?",
            "What is the difference between mean, median, and mode?",
            "Explain what a p-value is in hypothesis testing.",
            "What is exploratory data analysis (EDA)?",
            "What is the difference between classification and regression?",
        ],
        "medium": [
            "Explain the bias-variance tradeoff.",
            "How do you handle missing data in a dataset?",
            "What is cross-validation and why is it important?",
            "Explain how gradient descent works.",
            "What is the difference between bagging and boosting?",
            "How would you approach a highly imbalanced dataset?",
            "Explain the concept of feature engineering.",
            "What is regularization and why is it used?",
        ],
        "hard": [
            "Explain how transformers work in modern NLP models.",
            "How would you build a recommendation system from scratch?",
            "Explain the mathematics behind backpropagation in neural networks.",
            "How do you detect and handle data drift in a production ML model?",
            "Design an A/B testing framework for a large e-commerce platform.",
            "Explain how SHAP values work for model explainability.",
            "How would you approach building a fraud detection system?",
            "Explain the difference between generative and discriminative models.",
        ],
    },
    "Product Manager": {
        "easy": [
            "How do you define a product roadmap?",
            "What metrics do you use to measure product success?",
            "How do you prioritize features in a product backlog?",
            "What is the difference between a product manager and a project manager?",
            "How do you gather customer feedback?",
            "What is an MVP and why is it important?",
            "How do you handle conflicting stakeholder requirements?",
            "Describe your experience with agile methodology.",
        ],
        "medium": [
            "Walk me through how you would launch a new feature end-to-end.",
            "How do you measure the success of a product launch?",
            "Explain how you would conduct competitive analysis.",
            "How do you balance user needs vs. business goals?",
            "Describe a time you made a data-driven product decision.",
            "How do you work with engineering teams to scope features?",
            "What frameworks do you use for product strategy?",
            "How do you communicate product vision to different audiences?",
        ],
        "hard": [
            "You have 3 months, a team of 5 engineers, and need to increase retention by 20%. What do you do?",
            "How would you redesign a core feature that users hate but generates revenue?",
            "Describe how you would build a product strategy for entering a new market.",
            "How do you decide when to build vs buy vs partner?",
            "Walk me through how you would handle a major product failure post-launch.",
            "How would you manage a product with conflicting B2B and B2C requirements?",
            "Describe your approach to building a 3-year product vision.",
            "How do you prioritize technical debt vs new features?",
        ],
    },
    "General": {
        "easy": [
            "Tell me about yourself.",
            "What are your greatest strengths?",
            "What is your biggest weakness and how are you working on it?",
            "Why do you want to work at this company?",
            "Where do you see yourself in 5 years?",
            "What motivates you in your work?",
            "Describe your ideal work environment.",
            "What are your salary expectations?",
        ],
        "medium": [
            "Tell me about a time you had to work under pressure. How did you handle it?",
            "Describe a situation where you had to work with a difficult team member.",
            "Give me an example of when you took initiative at work.",
            "Tell me about your biggest professional failure and what you learned.",
            "How do you handle multiple deadlines at the same time?",
            "Describe a time you had to learn a new skill quickly.",
            "Tell me about a time you disagreed with your manager.",
            "How do you stay productive when working remotely?",
        ],
        "hard": [
            "Describe the most complex project you have ever led. What was your approach?",
            "Tell me about a time you had to make a decision without all the information you needed.",
            "Describe a time you had to influence people without direct authority.",
            "How have you handled a situation where the requirements changed mid-project?",
            "Tell me about a time you had to navigate organizational politics.",
            "Describe your biggest career risk and whether it paid off.",
            "How do you build trust with new team members in a remote environment?",
            "Tell me about a time you had to deliver hard feedback to a senior colleague.",
        ],
    },
}

KEYWORD_BANK = {
    "Software Engineer": ["algorithm", "data structure", "complexity", "scalable", "architecture",
                          "database", "API", "testing", "deployment", "performance", "security",
                          "agile", "version control", "git", "code review", "microservices"],
    "Data Scientist": ["model", "accuracy", "precision", "recall", "feature", "dataset", "training",
                       "validation", "neural network", "machine learning", "statistical", "hypothesis",
                       "correlation", "regression", "classification", "optimization"],
    "Product Manager": ["roadmap", "stakeholder", "metrics", "KPI", "user research", "agile",
                        "sprint", "backlog", "prioritization", "revenue", "retention", "conversion",
                        "customer", "data-driven", "strategy", "launch"],
    "General": ["teamwork", "leadership", "communication", "problem-solving", "initiative",
                "deadline", "collaboration", "adaptability", "feedback", "improvement",
                "goal", "strategy", "responsibility", "outcome", "impact"],
}

EMOTIONS = ["confident", "nervous", "calm", "engaged", "thoughtful", "focused", "uncertain", "enthusiastic"]

# ── AI Question Generator ──────────────────────────────────────────────────────

def generate_questions(job_role, difficulty, count=5, resume_skills=None):
    """
    Pick `count` questions for the given role/difficulty.
    If resume_skills are provided, prepend a tailored skills question.
    """
    bank = QUESTION_BANK.get(job_role, QUESTION_BANK["General"])
    pool = bank.get(difficulty, bank["medium"])

    selected = random.sample(pool, min(count, len(pool)))

    # Add resume-tailored question if skills were extracted
    if resume_skills:
        skills_list = ", ".join(resume_skills[:5])
        tailored = (
            f"I can see from your resume that you have experience with {skills_list}. "
            f"Can you tell me about a specific project where you used these skills and the impact you made?"
        )
        selected.insert(1, tailored)

    return selected


def score_answer(answer_text, question, job_role):
    """
    Score an answer on a 0–100 scale using keyword matching
    and heuristics (length, filler words, structure).
    Returns (score, keywords_found).
    """
    if not answer_text or len(answer_text.strip()) < 10:
        return 0, 0

    text_lower = answer_text.lower()
    keywords = KEYWORD_BANK.get(job_role, KEYWORD_BANK["General"])

    keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    keyword_score = min(keyword_hits * 8, 40)  # max 40 pts from keywords

    word_count = len(answer_text.split())
    if word_count < 20:
        length_score = 10
    elif word_count < 50:
        length_score = 20
    elif word_count < 150:
        length_score = 30
    else:
        length_score = 20  # slight penalty for rambling

    # Structure bonus: STAR method indicators
    star_words = ["situation", "task", "action", "result", "because", "therefore",
                  "first", "then", "finally", "example", "specifically", "implemented"]
    structure_hits = sum(1 for sw in star_words if sw in text_lower)
    structure_score = min(structure_hits * 3, 20)

    filler_words = ["um", "uh", "like", "you know", "basically", "literally"]
    filler_count = sum(text_lower.count(fw) for fw in filler_words)
    filler_penalty = min(filler_count * 2, 10)

    total = keyword_score + length_score + structure_score - filler_penalty
    total = max(0, min(100, total + random.randint(-5, 10)))  # small variance
    return round(total, 1), keyword_hits


def extract_skills_from_resume(content):
    """
    Simple rule-based skill extractor from resume text.
    Returns a list of detected skill tokens.
    """
    skill_patterns = [
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node.js", "flask", "django", "fastapi", "sql", "mysql", "postgresql",
        "mongodb", "redis", "docker", "kubernetes", "aws", "azure", "gcp",
        "machine learning", "deep learning", "tensorflow", "pytorch", "nlp",
        "agile", "scrum", "jira", "git", "ci/cd", "rest api", "graphql",
        "html", "css", "tailwind", "bootstrap", "linux", "bash", "r", "scala",
        "spark", "hadoop", "tableau", "power bi", "excel", "figma",
    ]
    content_lower = content.lower()
    found = [skill for skill in skill_patterns if skill in content_lower]
    return list(set(found))


# ── Routes: Auth ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            flash("Welcome back, " + user["username"] + "!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password))
            )
            db.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email or username already exists.", "error")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ── Routes: Dashboard ──────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    db   = get_db()
    uid  = session["user_id"]

    interviews = db.execute(
        "SELECT * FROM interviews WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        (uid,)
    ).fetchall()

    stats = db.execute("""
        SELECT
            COUNT(*)              AS total_interviews,
            ROUND(AVG(score), 1)  AS avg_score,
            MAX(score)            AS best_score,
            SUM(duration_sec)     AS total_time
        FROM interviews WHERE user_id = ?
    """, (uid,)).fetchone()

    resume = db.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
        (uid,)
    ).fetchone()

    # Chart data: last 7 interviews scores
    chart_data = db.execute(
        "SELECT created_at, score FROM interviews WHERE user_id = ? ORDER BY created_at DESC LIMIT 7",
        (uid,)
    ).fetchall()
    chart_data = list(reversed(chart_data))

    return render_template(
        "dashboard.html",
        interviews=interviews,
        stats=stats,
        resume=resume,
        chart_labels=json.dumps([r["created_at"][:10] for r in chart_data]),
        chart_scores=json.dumps([r["score"] for r in chart_data]),
    )


# ── Routes: Resume ─────────────────────────────────────────────────────────────

@app.route("/upload_resume", methods=["POST"])
@login_required
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files["resume"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file type. Use PDF or TXT."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Read text content (for .txt files; for PDF we read raw bytes as fallback)
    try:
        with open(filepath, "r", errors="ignore") as f:
            content = f.read()
    except Exception:
        content = ""

    skills = extract_skills_from_resume(content)

    db = get_db()
    uid = session["user_id"]
    # Remove old resumes for this user
    db.execute("DELETE FROM resumes WHERE user_id = ?", (uid,))
    db.execute(
        "INSERT INTO resumes (user_id, filename, content, skills) VALUES (?, ?, ?, ?)",
        (uid, filename, content[:5000], json.dumps(skills))
    )
    db.commit()

    return jsonify({
        "success": True,
        "filename": filename,
        "skills": skills,
        "skill_count": len(skills),
    })


# ── Routes: Interview ──────────────────────────────────────────────────────────

@app.route("/interview")
@login_required
def interview():
    """Interview setup page."""
    db     = get_db()
    resume = db.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
        (session["user_id"],)
    ).fetchone()
    return render_template("interview.html", resume=resume)


@app.route("/api/start_interview", methods=["POST"])
@login_required
def start_interview():
    """Create a new interview session and return the first set of questions."""
    data       = request.json or {}
    job_role   = data.get("job_role", "General")
    difficulty = data.get("difficulty", "medium")
    q_count    = int(data.get("question_count", 5))

    db  = get_db()
    uid = session["user_id"]

    # Fetch resume skills if available
    resume = db.execute(
        "SELECT skills FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
        (uid,)
    ).fetchone()
    resume_skills = json.loads(resume["skills"]) if resume and resume["skills"] else None

    questions = generate_questions(job_role, difficulty, q_count, resume_skills)

    # Create interview record
    cur = db.execute(
        "INSERT INTO interviews (user_id, job_role, difficulty, total_questions, resume_used) VALUES (?, ?, ?, ?, ?)",
        (uid, job_role, difficulty, len(questions), 1 if resume_skills else 0)
    )
    db.commit()
    interview_id = cur.lastrowid

    return jsonify({
        "success": True,
        "interview_id": interview_id,
        "questions": questions,
        "job_role": job_role,
        "difficulty": difficulty,
    })


@app.route("/api/submit_answer", methods=["POST"])
@login_required
def submit_answer():
    """Score one answer and store it."""
    data         = request.json or {}
    interview_id = data.get("interview_id")
    question     = data.get("question", "")
    answer_text  = data.get("answer", "")
    emotion      = data.get("emotion", random.choice(EMOTIONS))
    confidence   = float(data.get("confidence", random.uniform(50, 95)))
    job_role     = data.get("job_role", "General")

    score, kw_hits = score_answer(answer_text, question, job_role)

    db = get_db()
    db.execute(
        """INSERT INTO answers
           (interview_id, question, answer, score, emotion, confidence, keywords_hit)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (interview_id, question, answer_text, score, emotion, round(confidence, 1), kw_hits)
    )
    db.commit()

    return jsonify({
        "success": True,
        "score": score,
        "keywords_hit": kw_hits,
        "emotion": emotion,
        "confidence": round(confidence, 1),
        "feedback": _generate_feedback(score),
    })


def _generate_feedback(score):
    """Return brief qualitative feedback based on score."""
    if score >= 80:
        return random.choice([
            "Excellent answer! You demonstrated strong knowledge.",
            "Outstanding response with great use of specific examples.",
            "Impressive! Clear, structured, and insightful answer.",
        ])
    elif score >= 60:
        return random.choice([
            "Good answer. Try to include more specific examples.",
            "Solid response! Adding metrics or outcomes would strengthen it.",
            "Nice work. Consider using the STAR method for behavioral questions.",
        ])
    elif score >= 40:
        return random.choice([
            "Decent attempt. Focus on clarity and concrete details.",
            "You're on the right track. Add more depth to your explanation.",
            "Try to structure your answer better and give specific examples.",
        ])
    else:
        return random.choice([
            "Keep practicing! Focus on understanding the core concepts.",
            "This needs more work. Review the topic and try again.",
            "Don't worry — practice makes perfect. Aim for structured responses.",
        ])


@app.route("/api/finish_interview", methods=["POST"])
@login_required
def finish_interview():
    """Compute final scores, update the interview record, and return summary."""
    data         = request.json or {}
    interview_id = data.get("interview_id")
    duration     = int(data.get("duration_sec", 0))

    db = get_db()
    answers = db.execute(
        "SELECT score, emotion, confidence FROM answers WHERE interview_id = ?",
        (interview_id,)
    ).fetchall()

    if not answers:
        return jsonify({"success": False, "error": "No answers recorded"}), 400

    avg_score      = round(sum(a["score"]      for a in answers) / len(answers), 1)
    avg_confidence = round(sum(a["confidence"] for a in answers) / len(answers), 1)

    # Emotion scoring: give higher value to positive emotions
    positive_emotions = {"confident", "enthusiastic", "engaged", "focused"}
    emotion_score = round(
        (sum(1 for a in answers if a["emotion"] in positive_emotions) / len(answers)) * 100,
        1
    )

    db.execute("""
        UPDATE interviews
        SET score = ?, emotion_score = ?, confidence_avg = ?, duration_sec = ?
        WHERE id = ?
    """, (avg_score, emotion_score, avg_confidence, duration, interview_id))
    db.commit()

    # Compile per-answer breakdown
    breakdown = db.execute(
        "SELECT question, answer, score, emotion, confidence, keywords_hit FROM answers WHERE interview_id = ?",
        (interview_id,)
    ).fetchall()

    return jsonify({
        "success": True,
        "avg_score": avg_score,
        "emotion_score": emotion_score,
        "confidence_avg": avg_confidence,
        "duration_sec": duration,
        "breakdown": [dict(r) for r in breakdown],
        "grade": _grade(avg_score),
    })


def _grade(score):
    if score >= 85: return "A"
    if score >= 75: return "B"
    if score >= 65: return "C"
    if score >= 50: return "D"
    return "F"


# ── Routes: Results ────────────────────────────────────────────────────────────

@app.route("/results/<int:interview_id>")
@login_required
def results(interview_id):
    db        = get_db()
    uid       = session["user_id"]
    interview = db.execute(
        "SELECT * FROM interviews WHERE id = ? AND user_id = ?",
        (interview_id, uid)
    ).fetchone()

    if not interview:
        flash("Interview not found.", "error")
        return redirect(url_for("dashboard"))

    answers = db.execute(
        "SELECT * FROM answers WHERE interview_id = ? ORDER BY id",
        (interview_id,)
    ).fetchall()

    return render_template("results.html", interview=interview, answers=answers)


# ── Routes: API – misc ─────────────────────────────────────────────────────────

@app.route("/api/emotion_update", methods=["POST"])
@login_required
def emotion_update():
    """
    Receive base64 frame from the webcam; return a simulated emotion + confidence.
    (In a real deployment you would run a CV model here.)
    """
    # Simulate emotion detection — replace with a real model if desired
    emotion    = random.choices(
        EMOTIONS,
        weights=[20, 10, 20, 15, 15, 10, 5, 5]
    )[0]
    confidence = round(random.uniform(55, 98), 1)
    return jsonify({"emotion": emotion, "confidence": confidence})


@app.route("/api/stats")
@login_required
def api_stats():
    """Return JSON stats for the dashboard charts."""
    db  = get_db()
    uid = session["user_id"]

    role_data = db.execute("""
        SELECT job_role, ROUND(AVG(score),1) as avg_score, COUNT(*) as count
        FROM interviews WHERE user_id = ?
        GROUP BY job_role
    """, (uid,)).fetchall()

    emotion_data = db.execute("""
        SELECT emotion, COUNT(*) as count
        FROM answers
        JOIN interviews ON answers.interview_id = interviews.id
        WHERE interviews.user_id = ?
        GROUP BY emotion
    """, (uid,)).fetchall()

    return jsonify({
        "roles":    [dict(r) for r in role_data],
        "emotions": [dict(r) for r in emotion_data],
    })


# ── Initialise DB and Run ──────────────────────────────────────────────────────

# ── Jinja2 custom filter ───────────────────────────────────────────────────────

@app.template_filter("from_json")
def from_json_filter(value):
    """Parse a JSON string into a Python object (for use in templates)."""
    try:
        return json.loads(value)
    except Exception:
        return []


with app.app_context():
    init_db()

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  AI-Powered Smart Interview Assistant")
    print("  Running at: http://127.0.0.1:5000")
    print("="*55 + "\n")
    app.run(debug=True, port=5000)
