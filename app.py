# app.py
import os
from datetime import datetime, timedelta
from random import sample as rand_sample
import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from dotenv import load_dotenv

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

# ----------------- APP & DB SETUP -----------------
app = Flask(__name__)
load_dotenv()  
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-not-for-prod")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///Sam.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Upload settings
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
import requests  # <-- add this

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "your-minimax-api-key")
MINIMAX_VOICE_ID = os.environ.get("MINIMAX_VOICE_ID", "your-clone-voice-id")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------- MODELS -----------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200), nullable=True)
    quote = db.Column(db.String(300), nullable=False, default="Stay focused. Keep leveling up.")
    rank = db.Column(db.String(50), default="Bronze")
    level = db.Column(db.Integer, default=1)
    points = db.Column(db.Integer, default=0)
    strength = db.Column(db.Integer, default=50)
    health = db.Column(db.Integer, default=50)
    growth = db.Column(db.Integer, default=50)
    wisdom = db.Column(db.Integer, default=50)
    finance = db.Column(db.Integer, default=50)

    # Personal
    age = db.Column(db.Integer, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    fitness_level = db.Column(db.String(50), default="Beginner")

    # Quest timestamps
    last_daily_quest = db.Column(db.DateTime, default=None)
    last_weekly_quest = db.Column(db.DateTime, default=None)
    last_monthly_quest = db.Column(db.DateTime, default=None)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    alarm_time = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("tasks", lazy=True))


class StudyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.String(50))
    ended_at = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StudyLog {self.subject} - {self.duration} min>"


class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # daily/weekly/monthly
    difficulty = db.Column(db.String(50), nullable=False)
    xp = db.Column(db.Integer, default=10)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ----------------- RANK/LEVEL/STATS UTIL -----------------
def get_rank(points: int) -> str:
    ranks = [
        ("E", 00, 999),
        ("E+", 1000, 1999),
        ("E++", 2000, 2999),
        ("D", 3000, 4999),
        ("D+", 5000, 6999),
        ("D++", 7000, 8999),
        ("C", 9000, 11999),
        ("C+", 12000, 14999),
        ("C++", 15000, 17999),
        ("B", 18000, 21999),
        ("B+", 22000, 25999),
        ("B++", 26000, 29999),
        ("A", 30000, 34999),
        ("A+", 35000, 39999),
        ("A++", 40000, 44999),
        ("S", 45000, 49999),
        ("S+", 50000, 59999),
        ("SS", 60000, 69999),
        ("SS+", 70000, 79999),
        ("SSS", 80000, 89999),
        ("National Rank", 90000, 99999999),
    ]
    for rank, low, high in ranks:
        if low <= points <= high:
            return rank
    return "Unranked"


def get_level(points: int) -> int:
    level = 1
    thresholds = [50, 150, 300, 500, 750, 1050, 1400, 1800, 2250, 2750]
    for i, threshold in enumerate(thresholds, start=1):
        if points >= threshold:
            level = i + 1
    return level


def calculate_stats(user):
    base = user.points or 0
    # Simple derived stats — extend as you like
    completed_tasks = Task.query.filter_by(user_id=user.id, completed=True).count()
    completed_quests = Quest.query.filter_by(user_id=user.id, completed=True).count()
    completed_academics = StudyLog.query.filter_by(user_id=user.id).count()
    return {
        "strength": base // 10 + completed_tasks * 5,
        "finance": base // 20 + completed_academics * 3,
        "wisdom": base // 15 + completed_quests * 4,
        "growth": (completed_tasks + completed_academics + completed_quests) * 7,
        "mental": 50 + (base // 30),
    }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ----------------- QUEST POOLS & REGEN CONFIG -----------------
DEFAULT_POOLS = {
    "daily": [
        # Academics / Mental / Physical / Financial
        {"title": "Read 20 pages of a book", "category": "Academics", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Practice coding for 30 minutes", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Meditate for 10 minutes", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Do 20 push-ups", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Perform 10 pull-ups", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 25},
        {"title": "Solve 3 logic puzzles", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Spend 20 minutes learning finance basics", "category": "Financial", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Write down 3 business ideas", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 20},
        # Add 42 more daily quests
        {"title": "Read 1 chapter of a book daily", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Complete 3 coding exercises", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Meditate for 20 minutes total this week", "category": "Mental", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Do 100 push-ups total this week", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Attend 1 online workshop", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Solve 5 Sudoku puzzles", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Run or walk 10 km total this week", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Track all expenses for the week", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Plan next week’s schedule", "category": "Academics", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Learn 5 new logical reasoning techniques", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Practice MMA or self-defense 2 times", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Read an article on financial education", "category": "Financial", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Complete a mini coding project", "category": "Academics", "type": "weekly", "difficulty": "Hard", "xp": 70},
    {"title": "Do 50 burpees total this week", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Solve a weekly crossword puzzle", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Write a reflection journal for 3 days", "category": "Mental", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Try 1 new side hustle idea", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Do 3 strength training workouts", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Read 1 technical article", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Solve 10 brain teasers", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Complete 2 high-intensity cardio sessions", "category": "Physical", "type": "weekly", "difficulty": "Hard", "xp": 70},
    {"title": "Research 1 small business opportunity", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Practice 30 minutes of meditation daily", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Learn a new concept in your study field", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Plan 1 healthy meal plan for the week", "category": "Physical", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Do 3 flexibility exercises sessions", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Track your net worth weekly", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Solve 1 logic grid puzzle", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Complete 1 online quiz", "category": "Academics", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Do 3 sets of MMA drills", "category": "Physical", "type": "weekly", "difficulty": "Hard", "xp": 70},
    {"title": "Write 1 financial reflection journal", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Practice mindfulness daily for a week", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Complete 1 mini research project", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Run 5 km in a single session", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Complete 2 coding challenges", "category": "Academics", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Solve 5 puzzles with increasing difficulty", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Plan a budget for next week", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Do 3 full-body workouts", "category": "Physical", "type": "weekly", "difficulty": "Hard", "xp": 70},
    {"title": "Read 1 book summary", "category": "Academics", "type": "weekly", "difficulty": "Easy", "xp": 40},
    {"title": "Practice visualization and mental focus exercises", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Complete 1 side hustle task", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 50},
    {"title": "Do 50 lunges per leg", "category": "Physical", "type": "weekly", "difficulty": "Medium", "xp": 60},
    {"title": "Learn and apply 1 new problem-solving strategy", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},

    ] + [
        {"title": f"Daily Quest #{i}", "category": "Mixed", "type": "daily", "difficulty": "Easy", "xp": 10+i}
        for i in range(9, 51)
    ],

    "weekly": [
        {"title": "Finish one small project", "category": "Project", "type": "weekly", "difficulty": "Hard", "xp": 80},
        {"title": "Workout 4 times this week", "category": "Physical", "type": "weekly", "difficulty": "Hard", "xp": 70},
        {"title": "Solve 10 logic problems", "category": "Mental", "type": "weekly", "difficulty": "Medium", "xp": 50},
        {"title": "Research 3 side hustles", "category": "Financial", "type": "weekly", "difficulty": "Medium", "xp": 40},
        # Add 46 more weekly quests
        {"title": "Stretch for 10 minutes", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Do 30 squats", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Practice shadow boxing for 15 minutes", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 25},
        {"title": "Run 2 km", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Try 5 new yoga poses", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Solve 5 Sudoku puzzles", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Complete a brain teaser", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Practice memory exercise for 10 minutes", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Write a journal entry", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Learn 5 new vocabulary words", "category": "Academics", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Review 10 math problems", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Read an article on finance", "category": "Financial", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Track your daily expenses", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 15},
        {"title": "Plan tomorrow’s budget", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Do 15 lunges per leg", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Meditate using guided audio", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Solve 2 logic grid puzzles", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 25},
        {"title": "Learn a new programming concept", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 25},
        {"title": "Watch an educational video", "category": "Academics", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Practice 5 minutes of mindfulness breathing", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Do 50 jumping jacks", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Perform 20 sit-ups", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Learn about investing basics", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Research 1 small business idea", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Solve a daily crossword", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Practice deep breathing for 5 minutes", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Read a news article and summarize it", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Practice a new skill for 15 minutes", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Walk 3 km", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Practice MMA combinations for 10 minutes", "category": "Physical", "type": "daily", "difficulty": "Hard", "xp": 30},
        {"title": "Solve 3 brain teasers", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Complete a small coding challenge", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 25},
        {"title": "Track your daily water intake", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Plan your weekly fitness schedule", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Spend 15 minutes learning a new language", "category": "Academics", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Solve a math puzzle", "category": "Mental", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Check your savings progress", "category": "Financial", "type": "daily", "difficulty": "Easy", "xp": 15},
        {"title": "Research a side hustle opportunity", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Practice 10 burpees", "category": "Physical", "type": "daily", "difficulty": "Medium", "xp": 25},
        {"title": "Do 5 minutes of stretching after workout", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Write down 3 things you are grateful for", "category": "Mental", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Read a short article on finance", "category": "Financial", "type": "daily", "difficulty": "Easy", "xp": 10},
        {"title": "Create a mini budget for today", "category": "Financial", "type": "daily", "difficulty": "Medium", "xp": 20},
        {"title": "Practice shadow boxing for 5 minutes", "category": "Physical", "type": "daily", "difficulty": "Easy", "xp": 15},

    ] + [
        {"title": f"Weekly Quest #{i}", "category": "Mixed", "type": "weekly", "difficulty": "Medium", "xp": 40+i}
        for i in range(5, 51)
    ],

    "monthly": [
        {"title": "Complete a mini-course", "category": "Academics", "type": "monthly", "difficulty": "Hard", "xp": 200},
        {"title": "Read a full book", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 150},
        {"title": "Complete a financial plan for the month", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 180},
        {"title": "Achieve a fitness milestone", "category": "Physical", "type": "monthly", "difficulty": "Hard", "xp": 170},
        {"title": "Solve 50 logic puzzles", "category": "Mental", "type": "monthly", "difficulty": "Hard", "xp": 160},
        {"title": "Complete a 30-day workout challenge", "category": "Physical", "type": "monthly", "difficulty": "Hard", "xp": 180},
    {"title": "Learn a new programming language basics", "category": "Academics", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Meditate 15 minutes daily for a month", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Read 2 books", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 180},
    {"title": "Track all monthly expenses", "category": "Financial", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Research and start one side hustle", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Complete 4 long-distance runs", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Solve 100 logic puzzles", "category": "Mental", "type": "monthly", "difficulty": "Hard", "xp": 180},
    {"title": "Complete one advanced coding project", "category": "Academics", "type": "monthly", "difficulty": "Hard", "xp": 220},
    {"title": "Write a summary of all books read this month", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Create a monthly investment plan", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Practice MMA or self-defense 8 times", "category": "Physical", "type": "monthly", "difficulty": "Hard", "xp": 180},
    {"title": "Learn 20 new logic puzzles techniques", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Complete one online course", "category": "Academics", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Track 30 days of mindfulness or journaling", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Create a small business prototype", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 220},
    {"title": "Read financial news daily", "category": "Financial", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Achieve a personal best in running or cycling", "category": "Physical", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Solve a complex puzzle game", "category": "Mental", "type": "monthly", "difficulty": "Hard", "xp": 180},
    {"title": "Practice a skill daily for a month (language, coding, etc.)", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Plan and follow a healthy meal plan", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Write a monthly reflection journal", "category": "Mental", "type": "monthly", "difficulty": "Easy", "xp": 120},
    {"title": "Learn investment strategies for beginners", "category": "Financial", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Attend a workshop or webinar", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Complete 20 home workouts", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Solve 200 logic or brain puzzles", "category": "Mental", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Read a book on entrepreneurship", "category": "Financial", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Start a journal of 30 daily entries", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Complete a 30-day flexibility challenge", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Create a monthly financial report for personal finances", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Complete a 30-day coding challenge", "category": "Academics", "type": "monthly", "difficulty": "Hard", "xp": 220},
    {"title": "Plan and execute one mini-project", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Perform 3 hours of cardio per week", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Meditate daily for 15 minutes", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Research and learn a new side hustle", "category": "Financial", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Write a 5-page essay on a chosen topic", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Complete a 30-day strength training challenge", "category": "Physical", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Solve 50 advanced brain teasers", "category": "Mental", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Learn budgeting and track monthly expenses", "category": "Financial", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Read one personal development book", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Complete 4 long-distance cycling sessions", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 170},
    {"title": "Practice meditation and journaling together for 30 days", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Start a small entrepreneurial project", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Complete 10 high-intensity interval workouts", "category": "Physical", "type": "monthly", "difficulty": "Hard", "xp": 180},
    {"title": "Learn and apply problem-solving techniques", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Write a monthly plan with goals and milestones", "category": "Academics", "type": "monthly", "difficulty": "Medium", "xp": 160},
    {"title": "Track and analyze monthly fitness progress", "category": "Physical", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Read a book on mental health or mindfulness", "category": "Mental", "type": "monthly", "difficulty": "Medium", "xp": 150},
    {"title": "Complete a finance-related online course", "category": "Financial", "type": "monthly", "difficulty": "Hard", "xp": 200},
    {"title": "Complete a personal 30-day challenge of your choice", "category": "Mixed", "type": "monthly", "difficulty": "Medium", "xp": 160},
    ] + [
        {"title": f"Monthly Quest #{i}", "category": "Mixed", "type": "monthly", "difficulty": "Medium", "xp": 150+i}
        for i in range(6, 51)
    ],
}

# How many to create per period
COUNTS = {"daily": 3, "weekly": 2, "monthly": 1}

# Seconds to wait before regenerating quests (approx)
REGEN = {
    "daily": 24 * 3600,  # 24 hours
    "weekly": 7 * 24 * 3600,  # 7 days
    "monthly": 30 * 24 * 3600,  # 30 days
}


def _choose_sample(pool, count):
    if not pool:
        return []
    if len(pool) <= count:
        return pool.copy()
    try:
        return rand_sample(pool, count)
    except ValueError:
        # fallback
        return pool[:count]


# ----------------- QUEST UTILITIES -----------------
def generate_quests_for_user(user_id, db_session=db, UserModel=User, QuestModel=Quest):
    """Generate quests for a user only when the regen period has passed."""
    user = db_session.session.get(UserModel, user_id) if hasattr(db_session, "session") else UserModel.query.get(user_id)
    if not user:
        return

    now = datetime.utcnow()
    periods = {
        "daily": (user.last_daily_quest, REGEN["daily"]),
        "weekly": (user.last_weekly_quest, REGEN["weekly"]),
        "monthly": (user.last_monthly_quest, REGEN["monthly"]),
    }

    for period, (last_time, regen_seconds) in periods.items():
        needs = False
        if not last_time:
            needs = True
        else:
            elapsed = (now - last_time).total_seconds()
            if elapsed >= regen_seconds:
                needs = True

        if not needs:
            continue

        # Delete old quests of this period
        old_quests = QuestModel.query.filter_by(user_id=user.id, type=period).all()
        for q in old_quests:
            db.session.delete(q)

        # Choose and add new quests from pool
        pool = DEFAULT_POOLS.get(period, [])
        chosen = _choose_sample(pool, COUNTS.get(period, 1))
        for q in chosen:
            quest = QuestModel(
                user_id=user.id,
                title=q["title"],
                category=q.get("category", "General"),
                type=q.get("type", period),
                difficulty=q.get("difficulty", "Medium"),
                xp=q.get("xp", 10),
                completed=False,
            )
            db.session.add(quest)

        # Personalized physical quest based on BMI (only daily)
        if period == "daily" and user.weight_kg and user.height_cm:
            try:
                bmi = user.weight_kg / ((user.height_cm / 100) ** 2)
                title, xp = "Standard Exercise", 10
                if bmi < 18.5:
                    title, xp = "Light Workout", 15
                elif bmi > 25:
                    title, xp = "Moderate Cardio", 20
                # don't duplicate same title for same day
                exists = QuestModel.query.filter_by(user_id=user.id, title=title, type="daily").first()
                if not exists:
                    q = QuestModel(
                        user_id=user.id,
                        title=title,
                        category="Physical",
                        type="daily",
                        difficulty="Medium",
                        xp=xp,
                        completed=False,
                    )
                    db.session.add(q)
            except Exception:
                pass

        # Update last time
        if period == "daily":
            user.last_daily_quest = now
        elif period == "weekly":
            user.last_weekly_quest = now
        elif period == "monthly":
            user.last_monthly_quest = now

    db.session.commit()


def get_user_quests(user_id, period=None, QuestModel=Quest):
    """Return all quests for user; if period provided filter by type."""
    q = QuestModel.query.filter_by(user_id=user_id)
    if period:
        q = q.filter_by(type=period)
    return q.order_by(QuestModel.created_at.desc()).all()


def complete_user_quest(user_id, quest_id, QuestModel=Quest, UserModel=User):
    quest = QuestModel.query.get(quest_id)
    if not quest or quest.user_id != user_id:
        return False, "Quest not found or not owned by user"
    if quest.completed:
        return False, "Quest already completed"
    quest.completed = True
    user = UserModel.query.get(user_id)
    user.points = (user.points or 0) + (quest.xp or 0)
    # Optionally update user level/rank fields
    user.level = get_level(user.points)
    user.rank = get_rank(user.points)
    db.session.commit()
    return True, {"points": user.points, "quest_id": quest.id}


# ----------------- ROUTES -----------------
@app.route("/")
def home():
    return render_template("index.html")


# ----- AUTH -----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password_raw = request.form.get("password", "")
        quote = request.form.get("quote", "").strip() or "Stay focused. Keep leveling up."

        if not username or not password_raw:
            flash("Username and password required.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another one.", "danger")
            return render_template("register.html")

        password = generate_password_hash(password_raw)

        filename = None
        file = request.files.get("profile_pic")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Invalid image type.", "danger")
                return render_template("register.html")
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_user = User(username=username, password=password, profile_pic=filename, quote=quote)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("profile"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


# ----- PROFILE -----
@app.route("/profile")
@login_required
def profile():
    user_rank = get_rank(current_user.points or 0)
    user_level = get_level(current_user.points or 0)
    stats = calculate_stats(current_user)
    return render_template("dashboard/profile.html", user=current_user, rank=user_rank, level=user_level, stats=stats)


@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        if new_username and new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash("Username already taken.", "danger")
                return redirect(url_for("edit_profile"))
            current_user.username = new_username

        new_quote = request.form.get("quote")
        if new_quote:
            current_user.quote = new_quote

        file = request.files.get("profile_pic")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Invalid image type.", "danger")
                return redirect(url_for("edit_profile"))
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            current_user.profile_pic = filename

        current_user.age = request.form.get("age", type=int)
        current_user.height_cm = request.form.get("height_cm", type=float)
        current_user.weight_kg = request.form.get("weight_kg", type=float)
        current_user.fitness_level = request.form.get("fitness_level")

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    return render_template("dashboard/edit_profile.html", user=current_user)


# ----- TASKS -----
@app.route("/tasks")
@login_required
def tasks_page():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    return render_template("dashboard/tasks.html", tasks=tasks, user=current_user)


@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title')
    time_str = request.form.get('time')  # e.g., '2025-09-09T20:00'

    alarm_time = None
    if time_str:
        # Convert string from input to Python datetime
        alarm_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

    task = Task(
        user_id=current_user.id,
        title=title,
        completed=False,
        created_at=datetime.utcnow(),
        alarm_time=alarm_time  # now this is a proper datetime object
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for('tasks_page'))

@app.route("/complete_task/<int:task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({"success": False, "error": "Forbidden"}), 403
    if not task.completed:
        task.completed = True
        current_user.points = (current_user.points or 0) + 10
        current_user.strength = (current_user.strength or 0) + 2
        db.session.commit()
    return jsonify(success=True, points=current_user.points)


@app.route("/delete_task/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash("You cannot delete someone else's task.", "danger")
        return redirect(url_for("tasks_page"))
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks_list")
@login_required
def tasks_list():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    return jsonify([{"id": t.id, "title": t.title, "completed": t.completed} for t in tasks])


@app.route("/latest_task")
@login_required
def latest_task():
    task = Task.query.filter_by(user_id=current_user.id, completed=False).order_by(Task.created_at.desc()).first()
    return jsonify({"id": task.id, "title": task.title} if task else None)
@app.route('/modify_task/<int:task_id>', methods=['POST'])
def modify_task(task_id):
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'success': False, 'error': 'Title missing'}), 400
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    task.title = data['title']
    db.session.commit()
    return jsonify({'success': True})


# ----- ACADEMICS / STUDY LOGS -----
@app.route("/academics")
@login_required
def academics():
    return render_template("dashboard/academics.html", user=current_user)


@app.route("/add_study_log", methods=["POST"])
@login_required
def add_study_log():
    subject = request.form.get("subject", "Study")
    try:
        duration = int(request.form.get("duration", 0))
    except ValueError:
        duration = 0
    notes = request.form.get("notes", "")
    started_at = request.form.get("started_at", "")
    ended_at = request.form.get("ended_at", "")

    log = StudyLog(user_id=current_user.id, subject=subject, duration=duration, notes=notes, started_at=started_at, ended_at=ended_at)
    db.session.add(log)

    earned_points = max(1, duration // 5) if duration > 0 else 1
    current_user.points = (current_user.points or 0) + earned_points
    current_user.wisdom = (current_user.wisdom or 0) + (earned_points // 2)

    db.session.commit()
    return jsonify(success=True, points=current_user.points, earned=earned_points)


@app.route("/get_study_logs")
@login_required
def get_study_logs():
    logs = StudyLog.query.filter_by(user_id=current_user.id).order_by(StudyLog.created_at.desc()).all()
    data = [{"id": l.id, "subject": l.subject, "duration": l.duration, "notes": l.notes, "created_at": l.created_at.strftime("%Y-%m-%d %H:%M")} for l in logs]
    return jsonify(data)


@app.route("/delete_study_log/<int:log_id>", methods=["DELETE"])
@login_required
def delete_study_log(log_id):
    log = StudyLog.query.get_or_404(log_id)
    if log.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    db.session.delete(log)
    db.session.commit()
    return jsonify({"message": "Study log deleted successfully!"})


# ----- QUESTS -----
@app.route("/quests")
@login_required
def quests_page():
    # Ensure quests exist/up-to-date
    generate_quests_for_user(current_user.id)
    all_quests = get_user_quests(current_user.id)
    return render_template("dashboard/quests.html", quests=all_quests, user=current_user)


@app.route("/get_user_quests")
@login_required
def get_quests_api():
    period = request.args.get("period")
    quests = get_user_quests(current_user.id, period)
    quests_data = [
        {"id": q.id, "title": q.title, "category": q.category, "type": q.type, "difficulty": q.difficulty, "xp": q.xp, "completed": q.completed}
        for q in quests
    ]
    return jsonify(quests_data)


@app.route("/complete_quest", methods=["POST"])
@login_required
def complete_quest():
    data = request.json or {}
    quest_id = data.get("quest_id")
    if not quest_id:
        return jsonify({"success": False, "error": "Quest ID missing"}), 400
    success, result = complete_user_quest(current_user.id, int(quest_id))
    if not success:
        return jsonify({"success": False, "error": result}), 400
    return jsonify({"success": True, "points": result["points"], "quest_id": result["quest_id"]})


@app.route("/regenerate_quests")
@login_required
def regenerate_quests_api():
    generate_quests_for_user(current_user.id)
    return jsonify({"success": True, "message": "Quests regenerated successfully"})

@app.route("/voice_command", methods=["POST"])
@login_required
def voice_command():
    data = request.get_json() or {}
    cmd = (data.get("command") or "").lower().strip()
    response_text = "Sorry, I did not understand that command."

    try:
        # ========== Greetings ==========
        if any(word in cmd for word in ["hello", "hi", "hey", "what's up"]):
            response_text = f"Hi {current_user.username}, how can I assist you today?"
        elif "how are you" in cmd:
            response_text = "I'm doing great! Ready to help you with your productivity and growth."
        elif "good morning" in cmd:
            response_text = "Good morning! Let’s start your day strong."
        elif "good night" in cmd:
            response_text = "Good night! Rest well and recharge for tomorrow."

        # ========== Navigation ==========
        elif "tasks" in cmd:
            response_text = "Opening your tasks dashboard."
        elif "academics" in cmd or "study" in cmd:
            response_text = "Opening your academics dashboard."
        elif "quests" in cmd:
            response_text = "Opening your quests dashboard."
        elif "profile" in cmd or "my account" in cmd:
            response_text = "Opening your profile page."
        elif "developers" in cmd or "team" in cmd:
            response_text = "Opening the developers page."

        # ========== Task Management ==========
        elif "add task" in cmd:
            response_text = "Sure! Please enter the task title in your dashboard to add it."
        elif "complete task" in cmd:
            response_text = "Marking your selected task as complete."
        elif "delete task" in cmd or "remove task" in cmd:
            response_text = "Select a task in the dashboard to delete it."
        elif "list tasks" in cmd or "show tasks" in cmd:
            response_text = "Here are your current tasks on the dashboard."
        elif "next task" in cmd:
            response_text = "Your next pending task is highlighted on the dashboard."

        # ========== Quests ==========
        elif "add quest" in cmd:
            response_text = "To add a new quest, please go to the quests dashboard."
        elif "complete quest" in cmd:
            response_text = "Please select a quest to mark it as completed."
        elif "list quests" in cmd or "show quests" in cmd:
            response_text = "Here are your active quests."
        elif "daily quest" in cmd:
            response_text = "Today’s daily quest is waiting for you in the dashboard."

        # ========== Academics ==========
        elif "next exam" in cmd:
            response_text = "Fetching your next exam details from the academics dashboard."
        elif "study session" in cmd:
            response_text = "Starting a Pomodoro study session timer."
        elif "revision" in cmd or "revise" in cmd:
            response_text = "Reminder: It’s time for a quick revision session."
        elif "add subject" in cmd:
            response_text = "Please enter the new subject name in your academics dashboard."

        # ========== Motivation & Feedback ==========
        elif "motivate me" in cmd or "i'm tired" in cmd:
            response_text = "Stay strong! Remember why you started, success is on its way."
        elif "give me advice" in cmd:
            response_text = "Focus on one thing at a time. Consistency beats intensity."
        elif "congratulations" in cmd or "i finished" in cmd:
            response_text = "Great job! You’re one step closer to your goals."

        # ========== Utility ==========
        elif "time" in cmd:
            from datetime import datetime
            response_text = f"The current time is {datetime.now().strftime('%I:%M %p')}."
        elif "date" in cmd or "today" in cmd:
            from datetime import datetime
            response_text = f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
        elif "weather" in cmd:
            response_text = "Fetching the current weather for your location..."
        elif "help" in cmd or "commands" in cmd:
            response_text = "You can ask me to manage tasks, academics, quests, or motivate you."

        # ========== Terminate ==========
        elif "terminate" in cmd or "close assistant" in cmd or "stop listening" in cmd:
            response_text = "Voice assistant closed. Say 'Arise' to wake me up again."

    except Exception as e:
        response_text = f"Error processing command: {str(e)}"

    return jsonify({"success": True, "message": response_text})

# ----- DEVELOPERS / VIEW OTHER PROFILES -----
@app.route("/developers")
@login_required
def developers():
    developers = [
        {
            "id": 1,
            "name": "S.Imam Basha",
            "role": "Coordinator",
            "description": "Leads project vision & integration.",
            "photo": "mem1.jpg"
        },
        {
            "id": 2,
            "name": "S.Abdul Hameed",
            "role": "Backend Developer",
            "description": "Handles database & APIs.",
            "photo": ".jpg.jpeg"
        },
        {
            "id": 3,
            "name": "Sagabala Goutham",
            "role": "Frontend Developer",
            "description": "Designs UI/UX with neon theme.",
            "photo": "member3.jpg"
        },
        {
            "id": 4,
            "name": "M.Yashwanth Kumar",
            "role": "Tester",
            "description": "Ensures everything works smoothly.",
            "photo": ".jpg.jpeg"
        },
    ]

    return render_template("dashboard/developers.html", developers=developers)


@app.route("/developer/<int:dev_id>")
@login_required
def view_developer(dev_id):
    dev_user = User.query.get(dev_id)
    if not dev_user:
        return "Developer not found", 404
    return render_template("dashboard/profile_dev.html", user=dev_user)

@app.route("/ask", methods=["POST"])
def ask_ai():
    user_message = request.json.get("message")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek/deepseek-r1-0528:free",
        "messages": [{"role": "user", "content": user_message}]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                             headers=headers, json=data)

    return jsonify(response.json())


@app.route("/dashboard/spinwheel")
@login_required
def spinwheel_page():
    return render_template("dashboard/spinwheel.html")

@app.route("/spinwheel/complete", methods=["POST"])
@login_required
def spinwheel_complete():
    data = request.get_json()
    exercise = data.get("exercise")
    # Update user's points / XP in DB
    current_user.points += 10  # example
    db.session.commit()
    return jsonify({"success": True, "xp": 10})

# ------------------ new route ------------------
@app.route('/shufflecard')
@login_required
def shufflecard():
    return render_template('dashboard/shufflecard.html')

@app.route("/dashboard/quiz")
@login_required
def quiz_page():
    return render_template("dashboard/quiz.html")

@app.route("/logic")
@login_required
def logic():
    return render_template("dashboard/logic.html")

@app.route('/dashboard/memory')
def memory():
    return render_template('dashboard/memory.html')

@app.route('/worldbuild')
def worldbuild():
    return render_template('dashboard/worldbuild.html') 

@app.route('/dice')
def dice():
    return render_template('dashboard/dice.html')  # or just 'dice.html' if in templates/
 
@app.route("/coin")
@login_required
def coin_page():
    return render_template("dashboard/coin.html")

# API route to save XP
@app.route("/update_score", methods=["POST"])
@login_required
def update_score():
    data = request.get_json()
    score = data.get("score", 0)

    # Add score to user points
    current_user.points += score
    # Save to database
    db.session.commit()

    return jsonify({"success": True, "new_points": current_user.points})

@app.route("/budget")
@login_required
def budget_page():
    return render_template("dashboard/budget.html")
@app.route("/market")
@login_required
def market_page():
    return render_template("dashboard/market.html") 

@app.route('/save')
@login_required
def save_or_spend():

    return render_template("dashboard/save.html", user=current_user)

@app.route('/reset_save_game')
@login_required
def reset_save_game():

    current_user.bank = 0
    current_user.budget = 0
    return render_template("save.html", user=current_user)

@app.route('/money')
@login_required
def money_page():
    
    # You could also pass user-specific data if needed
    return render_template("dashboard/money.html", user=current_user)

@app.route('/build')
@login_required
def build_page():
    
    return render_template("dashboard/build.html", user=current_user)

@app.route('/course/<course_name>')
def course_page(course_name):
    # You can render different templates or dynamically show content based on the course
    return render_template('course_page.html', course=course_name)


# ----------------- STARTUP -----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True,port=8000)