
import sys
import os
import pytest
from google.cloud import firestore
from unittest.mock import MagicMock
from dotenv import load_dotenv

load_dotenv()

# Verify that the environment variable is set correctly
credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    print(f"GOOGLE_APPLICATION_CREDENTIALS is set to: {credentials_path}")
    if os.path.isfile(credentials_path):
        print("The credentials file exists.")
    else:
        print("The credentials file does not exist.")
else:
    print("GOOGLE_APPLICATION_CREDENTIALS is not set")


# Add the parent directory to sys.path to import modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import statements for the modules
from server.app import create_app 
from server.api_services.api_services import preprocess_text, send_to_google_nlp_api
from server.config import get_nlp_client
from server.models.User import User
from server.models.Task import Task

# pytest fixture for the app
@pytest.fixture
def app():
    app = create_app()
    return app

# app.py tests
def test_app_initialization(app):
    assert app is not None

def test_app_routes(app):
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200

# api_services.py tests
def test_preprocess_text():
    sample_text = "Natural Language Processing with Python is super fun!!"
    preprocessed = preprocess_text(sample_text)
    assert preprocessed is not None

def test_send_to_google_nlp_api(mocker):
    sample_text = "Natural Language Processing with Python is super fun!!"
    preprocessed = preprocess_text(sample_text)
    mock_response = MagicMock()
    mock_response.document_sentiment.score = 0.9
    mock_response.document_sentiment.magnitude = 1.2
    mock_response.sentences = ["Natural Language Processing with Python is super fun!!"]
    mocker.patch('server.api_services.api_services.get_nlp_client', return_value=mocker.Mock(analyze_sentiment=lambda x: mock_response))
    response = send_to_google_nlp_api(preprocessed)
    assert response is not None
    assert response.document_sentiment.score == 0.9

# config.py tests
def test_get_nlp_client():
    client = get_nlp_client()
    assert client is not None

# User.py tests
def test_user_creation():
    user = User(user_id="testuser", preferences={"theme": "dark"})
    assert user.user_id == "testuser"
    assert user.preferences["theme"] == "dark"

def test_user_password_hashing():
    user = User(user_id="testuser")
    user.set_password("password123")
    assert user.check_password("password123") is True
    assert user.check_password("wrongpassword") is False

# Tests the store_preferences method with mocking
def test_store_preferences(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    user = User(user_id="testuser", preferences={"theme": "dark"})
    user.store_preferences()
    user.db.collection('users').document.assert_called_once_with(user.user_id)
    user.db.collection('users').document(user.user_id).set.assert_called_once()

# Tests the analyze_mood method with mocked API calls
def test_analyze_mood(mocker):
    mocker.patch('server.api_services.api_services.preprocess_text', return_value="preprocessed text")
    mocker.patch('server.api_services.api_services.send_to_google_nlp_api', return_value=MagicMock())
    mocker.patch('server.api_services.api_services.parse_api_response', return_value=MagicMock())
    mocker.patch('server.api_services.api_services.extract_sentiment_score', return_value=0.9)
    mocker.patch('server.api_services.api_services.extract_keywords', return_value=["keyword1", "keyword2"])
    user = User(user_id="testuser")
    mood_analysis = user.analyze_mood("I am feeling very stressed out today")
    assert mood_analysis['sentimentScore'] == 0.9
    assert "keyword1" in mood_analysis['keywords']

# Tests the store_mood_analysis method with mocking
def test_store_mood_analysis(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    user = User(user_id="testuser")
    mood_analysis = {
        'inputText': "I am feeling very stressed out today",
        'sentimentScore': 0.9,
        'keywords': ["keyword1", "keyword2"],
        'moodCategory': "positive"
    }
    user.store_mood_analysis(mood_analysis)
    user.db.collection('moodAnalysis').document.assert_called_once()
    user.db.collection('moodAnalysis').document().set.assert_called_once_with({
        'userId': user.user_id,
        'inputText': mood_analysis['inputText'],
        'sentimentScore': mood_analysis['sentimentScore'],
        'keywords': mood_analysis['keywords'],
        'moodCategory': mood_analysis['moodCategory'],
        'timestamp': firestore.SERVER_TIMESTAMP
    })

# Tests the update_last_login method with mocking
def test_update_last_login(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    user = User(user_id="testuser")
    user.update_last_login()
    user.db.collection('users').document.assert_called_once_with(user.user_id)
    user.db.collection('users').document(user.user_id).update.assert_called_once_with({
        'lastLogin': firestore.SERVER_TIMESTAMP
    })

# Task.py tests
def test_task_creation():
    task = Task(description="This is a Sample Task")
    assert task.description == "This is a Sample Task"

def test_task_preprocess():
    task = Task(description="Natural Language Processing with Python is super fun!!")
    preprocessed = task.preprocess()
    assert preprocessed is not None




# Add tests for task_controller.py 
