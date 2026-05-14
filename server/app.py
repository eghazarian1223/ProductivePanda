import os
import random
from dotenv import load_dotenv
load_dotenv()

# Set credentials before any Google Cloud imports
_credentials_path = os.path.join(os.path.dirname(__file__), 'config', 'service_account.json')
if os.path.exists(_credentials_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _credentials_path

from flask import Flask, render_template, url_for, redirect, flash, request, jsonify
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, generate_csrf
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from server.extensions import db
from server.routes.tasks import task_controller, reorganize_tasks_based_on_mood
from server.models.user import MoodUser
from server.models.task import Task

bcrypt = Bcrypt()

UPLIFTING_SUGGESTIONS = [
    "Take a 5-minute walk outside",
    "Drink a glass of water",
    "Do 3 deep breaths",
    "Listen to your favorite song",
    "Text a friend to say hi",
    "Do one small, satisfying task",
    "Make yourself a warm drink",
    "Write down 3 things you're grateful for",
    "Step away from your screen for 5 minutes",
    "Do some light stretching",
]


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise RuntimeError('SECRET_KEY environment variable is not set')

    db.init_app(app)
    bcrypt.init_app(app)
    csrf = CSRFProtect(app)
    csrf.exempt(task_controller)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(task_controller, url_prefix='/tasks')

    with app.app_context():
        db.create_all()

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Invalid username or password.', 'error')
        return render_template('login.html', form=form)

    @app.route('/dashboard', methods=['GET', 'POST'])
    @login_required
    def dashboard():
        mood_analysis = None
        suggestions = []
        tasks = Task.query.filter_by(user_id=current_user.id, completed=False).order_by(Task.created_at.desc()).all()
        reorganized_tasks = tasks

        if request.method == 'POST':
            input_text = request.form.get('inputText', '').strip()
            if input_text:
                mood_user = MoodUser(user_id=current_user.id)
                mood_analysis = mood_user.analyze_mood(input_text)
                mood_user.store_mood_analysis(mood_analysis)
                score = mood_analysis['sentimentScore']
                reorganized_tasks = reorganize_tasks_based_on_mood(tasks, score)
                if score < -0.25:
                    suggestions = random.sample(UPLIFTING_SUGGESTIONS, min(3, len(UPLIFTING_SUGGESTIONS)))

        return render_template('dashboard.html',
                               name=current_user.username,
                               mood_analysis=mood_analysis,
                               tasks=reorganized_tasks,
                               suggestions=suggestions)

    @app.route('/logout', methods=['GET', 'POST'])
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = RegisterForm(request.form)
        if request.method == 'POST' and form.validate():
            try:
                hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
                new_user = User(username=form.username.data, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login'))
            except Exception as e:
                flash(f"An error occurred: {str(e)}")
                app.logger.error(f"Registration error: {str(e)}")
                return redirect(url_for('register'))
        return render_template('register.html', form=form)

    @app.route('/todo')
    @login_required
    def todo():
        return render_template('todo.html')

    @app.route('/store_preferences', methods=['POST'])
    @login_required
    def store_preferences():
        preferences = request.json.get('preferences')
        mood_user = MoodUser(user_id=current_user.id, preferences=preferences)
        mood_user.store_preferences()
        return jsonify({"message": "Preferences stored successfully"})

    return app


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError("That username already exists. Please choose a different one.")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username", "class": "login-input-field"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password", "class": "login-input-field"})
    submit = SubmitField("Login", render_kw={"class": "app-login-button"})


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
