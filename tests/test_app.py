
import sys
import os
import pytest
from google.cloud import firestore
from unittest.mock import patch, MagicMock
from flask import Flask
from dotenv import load_dotenv
from pytest_socket import disable_socket, enable_socket
import logging

from server.app import create_app
from server.routes.tasks import task_controller, reorganize_tasks_based_on_mood_and_sentiment
from server.config.config import get_nlp_client
from server.models.user import User, MoodUser
from server.models.task import Task
from server.services.nlp import preprocess_text, send_to_google_nlp_api, parse_api_response, extract_sentiment_score, extract_keywords

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    return app.test_client()


# app tests
def test_app_initialization(app):
    assert app is not None

def test_app_routes(app):
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200


# nlp.py tests
def test_preprocess_text():
    sample_text = "Natural Language Processing with Python is super fun!!"
    preprocessed = preprocess_text(sample_text)
    assert preprocessed is not None

def test_send_to_google_nlp_api(mocker):
    sample_text = "Natural Language Processing with Python is super fun!!"
    preprocessed = preprocess_text(sample_text)

    mock_response = {
        "document_sentiment": {"score": 0.9, "magnitude": 1.2},
        "sentences": [
            {
                "text": {"content": sample_text, "begin_offset": -1},
                "sentiment": {"score": 0.9, "magnitude": 1.2}
            }
        ]
    }

    mocker.patch('server.services.nlp.get_nlp_client', return_value=mocker.Mock(analyze_sentiment=lambda document: mock_response))
    response = send_to_google_nlp_api(preprocessed)
    assert response is not None
    assert response["document_sentiment"]["score"] == 0.9

def test_preprocessing_text():
    test_cases = [
        ("I'm not happy with this service.", "not happy service"),
        ("The movie was good, but the ending was not.", "movie good but ending not"),
        ("I love it!", "love"),
        ("It's ok.", "ok"),
        ("Terrible service, never coming back!", "terrible service never coming back"),
        ("Can't believe it", "can not believe"),
        ("We'll", "we will"),
        ("Let's go!", "let us go")
    ]

    for original, expected in test_cases:
        preprocessed = preprocess_text(original)
        assert preprocessed == expected, f"Failed for {original}: got {preprocessed}, expected {expected}"

def test_preprocessing_and_sentiment_analysis():
    test_cases = [
        ("I'm not happy with this service.", -0.8),
        ("The movie was good, but the ending was not.", 0.0),
        ("I love it!", 0.9),
        ("It's ok.", 0.1),
        ("Terrible service, never coming back!", -0.8)
    ]
    for text, expected_score in test_cases:
        preprocessed = preprocess_text(text)
        response = send_to_google_nlp_api(preprocessed)
        parsed_response = parse_api_response(response)
        actual_score = extract_sentiment_score(parsed_response, preprocessed_text=preprocessed)
        assert actual_score == pytest.approx(expected_score, abs=0.1)


# config.py tests
def test_get_nlp_client():
    client = get_nlp_client()
    assert client is not None


# user.py tests
def test_mood_user_creation():
    mood_user = MoodUser(user_id="testuser", preferences={"theme": "dark"})
    assert mood_user.user_id == "testuser"
    assert mood_user.preferences["theme"] == "dark"

def test_user_password_hashing():
    user = User(username="testuser")
    user.set_password("password123")
    assert user.check_password("password123") is True
    assert user.check_password("wrongpassword") is False

def test_store_preferences(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    mood_user = MoodUser(user_id="testuser", preferences={"theme": "dark"})
    mood_user.store_preferences()
    mood_user.db.collection('users').document.assert_called_once_with(mood_user.user_id)
    mood_user.db.collection('users').document(mood_user.user_id).set.assert_called_once()

def test_analyze_mood(mocker):
    disable_socket()
    try:
        mocker.patch('server.services.nlp.preprocess_text', return_value="preprocessed text")

        mock_response = {
            "document_sentiment": {"score": -0.8, "magnitude": 0.8},
            "sentences": [
                {
                    "text": {"content": "I'm not happy with this service.", "begin_offset": -1},
                    "sentiment": {"score": -0.8, "magnitude": 0.8}
                }
            ]
        }

        mocker.patch('server.services.nlp.send_to_google_nlp_api', return_value=mock_response)
        mocker.patch('server.services.nlp.parse_api_response', return_value={"score": -0.8, "magnitude": 0.8, "sentences": ["preprocessed text"]})
        mocker.patch('server.services.nlp.extract_sentiment_score', return_value=-0.8)
        mocker.patch('server.services.nlp.extract_keywords', return_value=["feeling", "stressed", "today"])

        mood_user = MoodUser(user_id="testuser")
        mood_analysis = mood_user.analyze_mood("I am feeling very stressed out today")
        assert "feeling" in mood_analysis['keywords']
        assert "stressed" in mood_analysis['keywords']
        assert "today" in mood_analysis['keywords']
    finally:
        enable_socket()

def test_store_mood_analysis_with_mock_encryption(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    mock_encrypt = lambda x: f'encrypted_{x}'

    mood_user = MoodUser(user_id="testuser")
    mood_analysis = {
        'inputText': "I am feeling very stressed out today",
        'sentimentScore': -0.8,
        'keywords': ["stressed", "today"],
        'moodCategory': "negative"
    }

    expected_encrypted_mood_analysis = {
        'inputText': 'encrypted_I am feeling very stressed out today',
        'sentimentScore': mood_analysis['sentimentScore'],
        'keywords': ['encrypted_stressed', 'encrypted_today'],
        'moodCategory': 'encrypted_negative',
        'timestamp': mocker.ANY
    }

    mood_user.store_mood_analysis(mood_analysis, encrypt_func=mock_encrypt)
    mood_user.db.collection('moodAnalysis').document.assert_called_once()
    mood_user.db.collection('moodAnalysis').document().set.assert_called_once_with(expected_encrypted_mood_analysis)


# task.py tests
def test_task_creation():
    task = Task(description="This is a Sample Task")
    assert task.description == "This is a Sample Task"

def test_task_preprocess():
    task = Task(description="Natural Language Processing with Python is super fun!!")
    preprocessed = task.preprocess()
    assert preprocessed is not None


# tasks route tests
def test_analyze_tasks_happy_path_positive(client, mocker):
    mocker.patch('server.models.user.MoodUser.analyze_mood', autospec=True, return_value={'moodCategory': 'positive'})
    mocker.patch('server.models.user.MoodUser.store_mood_analysis')
    mocker.patch('server.services.nlp.preprocess_text', side_effect=preprocess_text)
    mocker.patch('server.services.nlp.send_to_google_nlp_api', return_value={
        "documentSentiment": {"score": 0.9, "magnitude": 1.2},
        "sentences": [{"text": {"content": "task 1", "begin_offset": 0}, "sentiment": {"score": 0.9, "magnitude": 1.2}}]
    })
    mocker.patch('server.services.nlp.parse_api_response', return_value={"sentimentScore": 0.9})
    mocker.patch('server.services.nlp.extract_sentiment_score', return_value=0.9)
    mocker.patch('server.services.nlp.extract_keywords', return_value=["keyword1", "keyword2"])

    response = client.post('/tasks/analyze_tasks', json={"user_id": "testuser", 'text': 'I am feeling great today!'})
    assert response.status_code == 200
    response_json = response.get_json()
    assert response_json is not None
    assert 'recommendedTasks' in response_json
    assert response_json.get('userMoodCategory') == 'positive'

def test_analyze_tasks_happy_path_negative(client, mocker):
    mocker.patch('server.models.user.MoodUser.analyze_mood', autospec=True, return_value={'moodCategory': 'negative'})
    mocker.patch('server.models.user.MoodUser.store_mood_analysis')
    mocker.patch('server.services.nlp.preprocess_text', return_value="preprocessed task")
    mocker.patch('server.services.nlp.send_to_google_nlp_api', return_value={
        "documentSentiment": {"score": -0.8, "magnitude": 1.2},
        "sentences": [{"text": {"content": "task 1", "begin_offset": 0}, "sentiment": {"score": -0.8, "magnitude": 1.2}}]
    })
    mocker.patch('server.services.nlp.parse_api_response', return_value={"sentimentScore": -0.8})
    mocker.patch('server.services.nlp.extract_sentiment_score', return_value=-0.8)
    mocker.patch('server.services.nlp.extract_keywords', return_value=["keyword1", "keyword2"])

    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}, {"description": "task 2"}]}
    response = client.post('/tasks/analyze_tasks', json=data)
    assert response.status_code == 200
    response_json = response.get_json()
    assert response_json is not None
    assert 'recommendedTasks' in response_json
    assert response_json.get('userMoodCategory') == 'negative'

def test_analyze_tasks_happy_path_neutral(client, mocker):
    mocker.patch('server.models.user.MoodUser.analyze_mood', autospec=True, return_value={'moodCategory': 'neutral'})
    mocker.patch('server.models.user.MoodUser.store_mood_analysis')
    mocker.patch('server.services.nlp.preprocess_text', return_value="preprocessed task")
    mocker.patch('server.services.nlp.send_to_google_nlp_api', return_value={
        "documentSentiment": {"score": 0.0, "magnitude": 0.0},
        "sentences": [{"text": {"content": "task 1", "begin_offset": 0}, "sentiment": {"score": 0.0, "magnitude": 0.0}}]
    })
    mocker.patch('server.services.nlp.parse_api_response', return_value={"sentimentScore": 0.0})
    mocker.patch('server.services.nlp.extract_sentiment_score', return_value=0.0)
    mocker.patch('server.services.nlp.extract_keywords', return_value=["keyword1", "keyword2"])

    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}, {"description": "task 2"}]}
    response = client.post('/tasks/analyze_tasks', json=data)
    assert response.status_code == 200
    response_json = response.get_json()
    assert response_json is not None
    assert 'recommendedTasks' in response_json
    assert response_json.get('userMoodCategory') == 'neutral'

def test_analyze_tasks_exception_handling(client, mocker):
    mocker.patch('server.models.user.MoodUser.analyze_mood', side_effect=Exception("Something went wrong"))

    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}]}
    response = client.post('/tasks/analyze_tasks', json=data)
    assert response.status_code == 400
    assert "error" in response.json

def test_reorganize_tasks_based_on_mood_and_sentiment_positive(mocker):
    tasks = [
        {"description": "Task 1", "priority": 1},
        {"description": "Task 2", "priority": 3},
        {"description": "Task 3", "priority": 2}
    ]
    mock_analyze_sentiment = mocker.patch('server.routes.tasks.analyze_task_sentiment')
    mock_analyze_sentiment.side_effect = lambda text: 0.5

    expected_result = [
        {"description": "Task 2", "priority": 3, "sentiment_score": 0.5},
        {"description": "Task 3", "priority": 2, "sentiment_score": 0.5},
        {"description": "Task 1", "priority": 1, "sentiment_score": 0.5}
    ]
    assert reorganize_tasks_based_on_mood_and_sentiment(tasks, 1.0) == expected_result

def test_reorganize_tasks_based_on_mood_and_sentiment_negative(mocker):
    tasks = [
        {"description": "Task 1", "priority": 1},
        {"description": "Task 2", "priority": 3},
        {"description": "Task 3", "priority": 2}
    ]
    mock_analyze_sentiment = mocker.patch('server.routes.tasks.analyze_task_sentiment')
    mock_analyze_sentiment.side_effect = lambda text: -0.5

    expected_result = [
        {"description": "Task 1", "priority": 1, "sentiment_score": -0.5},
        {"description": "Task 3", "priority": 2, "sentiment_score": -0.5},
        {"description": "Task 2", "priority": 3, "sentiment_score": -0.5}
    ]
    assert reorganize_tasks_based_on_mood_and_sentiment(tasks, -1.0) == expected_result

def test_reorganize_tasks_based_on_mood_and_sentiment_neutral(mocker):
    tasks = [
        {"description": "Task 1", "priority": 1},
        {"description": "Task 2", "priority": 3},
        {"description": "Task 3", "priority": 2}
    ]
    mock_analyze_sentiment = mocker.patch('server.routes.tasks.analyze_task_sentiment')
    mock_analyze_sentiment.side_effect = lambda text: 0.0

    expected_result = [
        {"description": "Task 2", "priority": 3, "sentiment_score": 0.0},
        {"description": "Task 3", "priority": 2, "sentiment_score": 0.0},
        {"description": "Task 1", "priority": 1, "sentiment_score": 0.0}
    ]
    assert reorganize_tasks_based_on_mood_and_sentiment(tasks, 0.0) == expected_result
