from flask import Flask, render_template, url_for, redirect, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from server.models.User import User as MoodUser
from google.cloud import firestore 
from server.config.config import get_nlp_client

db_firestore = firestore.Client()

app = Flask(__name__, template_folder='templates', static_folder='frontend')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:\\Users\\eghaz\\Downloads\\ProductivePandaDoingAgain\\server\\database.db' # This might actually be the wrong one cuz apparently all of a sudden there are two (change accordingly)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'authenticationsecretkey'
db = SQLAlchemy(app)  
bcrypt = Bcrypt(app)
app.app_context().push()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Table
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True) # Unique Id for each user
    username = db.Column(db.String(20), nullable=False, unique=True) # Username will have maximum of 20 characters 
    # unique = True means not more than one can have same username
    password = db.Column(db.String(80), nullable=False) # Password will have maximum of 80 characters

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")
    # Distinguishes whether or not the username already exists
    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError("That username already exists. Please choose a different one.")

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username", "class": "login-input-field"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password", "class": "login-input-field"})
    submit = SubmitField("Login", render_kw={"class": "app-login-button"}) # render_kw part gives a class to login button to change its appearance
 

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


if __name__ == "__main__":
    app.run(debug=True)
    