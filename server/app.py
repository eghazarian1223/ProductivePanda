import os
from flask import Flask, render_template, url_for, redirect, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from google.cloud import firestore
from server.api.task_controller import task_controller
from server.models.user_sqlalchemy_firestore_models import User as MoodUser


db = SQLAlchemy()
bcrypt = Bcrypt()

def create_app():
    # Initialize Flask app
    app = Flask(__name__, template_folder='templates', static_folder='frontend')
    app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\eghaz\Downloads\ProductivePandaDoingAgain\server\database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'authenticationsecretkey'
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    
    # Initialize Firestore
    credentials_path = r"C:\Users\eghaz\Downloads\ProductivePandaDoingAgain\server\config\productivepandacredentials.json"
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    db_firestore = firestore.Client()
    
    # Set up Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprint
    app.register_blueprint(task_controller, url_prefix='/tasks')

    # Define routes
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
        return render_template('login.html', form=form)

    @app.route('/dashboard', methods=['GET', 'POST'])
    @login_required
    def dashboard():
        if request.method == 'POST':
            input_text = request.form.get('inputText')
            if input_text:
                mood_user = MoodUser(user_id=current_user.id)
                mood_analysis = mood_user.analyze_mood(input_text)
                mood_user.store_mood_analysis(mood_analysis)
                flash('Mood analysis complete!', 'success')
                return render_template('dashboard.html', name=current_user.username, mood_analysis=mood_analysis)
        return render_template('dashboard.html', name=current_user.username)

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

    @app.route('/add_document', methods=['POST'])
    @login_required
    def add_document():
        try:

            data = request.json
            if not data or not isinstance(data, dict):
                return jsonify({'status': 'Invalid data'}), 400
            db_firestore.collection('test_collection').document('test_doc').set(data)
            return jsonify({'status': 'Document added'})
        except Exception as e:
            app.logger.error(f"ERROR adding document: {e}")
            return jsonify({'status': 'Error adding document'}), 500

    @app.route('/get_document', methods=['POST'])
    @login_required
    def get_document():
        try:
            doc = db_firestore.collection('test_collection').document('test_doc').get()
            if doc.exists:
                return jsonify(doc.to_dict())
            else:
                return jsonify({'status': 'Document not found'}), 404
        except Exception as e:
            app.logger.error(f"Error retrieving document: {e}")
            return jsonify({'status': 'Error retrieving document'}), 500
    

    return app

# Define User model for the database
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

# Define forms
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
    app = create_app()  # Use create_app to initialize the app
    app.run(debug=True)
