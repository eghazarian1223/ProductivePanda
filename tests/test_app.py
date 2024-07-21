
import sys
import os
import pytest
from google.cloud import firestore
from unittest.mock import MagicMock
from dotenv import load_dotenv
from pytest_socket import disable_socket, enable_socket



#Loading environment variables and verifying their setup.
load_dotenv()
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

from server.app import create_app 
from server.api_services.api_services import preprocess_text, send_to_google_nlp_api, parse_api_response, extract_sentiment_score, extract_keywords

from server.config import get_nlp_client
from server.models.User import User
from server.models.Task import Task

# pytest fixture for the app
@pytest.fixture
def app():
    app = create_app()
    return app

# Test function requesting the fixture
def test_app_initialization(app):
    assert app is not None

# Another test function requesting the same fixture
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
    mock_response.sentences = [
        MagicMock(text=MagicMock(content="Natural Language Processing with Python is super fun!!", begin_offset=-1),
                  sentiment=MagicMock(score=0.9, magnitude=1.2))
    ]
    mocker.patch('server.api_services.api_services.get_nlp_client', return_value=mocker.Mock(analyze_sentiment=lambda document: mock_response))
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


def test_analyze_mood(mocker):
    disable_socket()

    try:
        # Mocking functions to return expected values
        mock_preprocess_text = mocker.patch('server.api_services.api_services.preprocess_text', return_value="preprocessed text")
        mock_response = MagicMock()
        mock_response.document_sentiment.score = 0.9
        mock_response.document_sentiment.magnitude = 1.2
        mock_response.sentences = [
            MagicMock(
                text=MagicMock(content="Natural Language Processing with Python is super fun!!", begin_offset=-1),
                sentiment=MagicMock(score=0.9, magnitude=1.2)
            )
        ]
        mock_send_to_google_nlp_api = mocker.patch('server.api_services.api_services.send_to_google_nlp_api', return_value=mock_response)
        mock_parsed_response = {"score": 0.9, "magnitude": 1.2, "sentences": ["preprocessed text"]}
        mock_parse_api_response = mocker.patch('server.api_services.api_services.parse_api_response', return_value=mock_parsed_response)
        mock_extract_sentiment_score = mocker.patch('server.api_services.api_services.extract_sentiment_score', return_value=0.9)
        mock_extract_keywords = mocker.patch('server.api_services.api_services.extract_keywords', return_value=["keyword1", "keyword2"])

        assert mock_preprocess_text is not None, "Failed to mock preprocess_text"
        assert mock_send_to_google_nlp_api is not None, "Failed to mock send_to_google_nlp_api"
        assert mock_parse_api_response is not None, "Failed to mock parse_api_response"
        assert mock_extract_sentiment_score is not None, "Failed to mock extract_sentiment_score"
        assert mock_extract_keywords is not None, "Failed to mock extract_keywords"

        print(f"Mock parse_api_response: {mock_parse_api_response(mock_response)}")
        print(f"Mock extract_sentiment_score: {mock_extract_sentiment_score(mock_parsed_response)}")
        print(f"Mock extract_keywords: {mock_extract_keywords(mock_parsed_response)}")


        user = User(user_id="testuser")

        print(f"Mock preprocess_text: {mock_preprocess_text('test')}")
        print(f"Mock send_to_google_nlp_api: {mock_send_to_google_nlp_api('test')}")
        print(f"Mock parse_api_response: {mock_parse_api_response(mock_response)}")
        print(f"Mock extract_sentiment_score: {mock_extract_sentiment_score(mock_parsed_response)}")
        print(f"Mock extract_keywords: {mock_extract_keywords(mock_parsed_response)}")

        assert mock_extract_sentiment_score(mock_parsed_response) == pytest.approx(0.9, rel=1e-6)
        assert mock_extract_keywords(mock_parsed_response) == ["keyword1", "keyword2"]
        mood_analysis = user.analyze_mood("I am feeling very stressed out today")
        print(f"mood_analysis returned from analyze_mood: {mood_analysis}")

        assert mood_analysis['sentimentScore'] == pytest.approx(0.9, rel=1e-6)
        assert "keyword1" in mood_analysis['keywords']
        assert "keyword2" in mood_analysis['keywords']
    
    finally:
        enable_socket()

    



    
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
