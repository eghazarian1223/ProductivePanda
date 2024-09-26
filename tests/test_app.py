
import sys
import os
import pytest
from google.cloud import firestore
from unittest.mock import patch, MagicMock, call
from flask import Flask, jsonify
from dotenv import load_dotenv
from pytest_socket import disable_socket, enable_socket
import logging
from cryptography.fernet import Fernet
from server.app import create_app
from server.api.task_controller import task_controller, decrypt_data ,compare_mood_with_tasks, recommend_general_uplifting_tasks, store_user_data_securely, retrieve_user_data_securely, delete_no_longer_needed_data
from server.app import create_app 
from server.config.config import get_nlp_client
from server.models.User import User
from server.models.User import MoodUser
from server.models.Task import Task
from server.api_handler.api_services import preprocess_text, send_to_google_nlp_api
from server.api.task_controller import reorganize_tasks_based_on_mood_and_sentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

key = os.getenv('ENCRYPTION_KEY')
if key is None:
    logger.error("ENCRYPTION_KEY environment variable not set")
    sys.exit(1)

try:
    cipher_suite = Fernet(key.encode())
except Exception as e:
    logger.error(f"Failed to initialize Fernet cipher: {e}")
    sys.exit(1)


plain_texts = [
    "I'm not happy with this service.",
    "The movie was good, but the ending was not.",
    "I love it!",
    "It's ok.",
    "Terrible service, never coming back!",
    "Can't believe it!",
    "We'll",
    "Let us go!"
]

encrypted_texts = [cipher_suite.encrypt(text.encode()).decode() for text in plain_texts]
for text, encrypted in zip(plain_texts, encrypted_texts):
    logger.info(f"Original: {text}\nEncrypted: {encrypted}\n")
  
def decrypt_text(encrypted_text):
    logger.debug(f"Attempting to decrypt text.")
    logger.debug(f"Encrypted text before decoding: {encrypted_text}")

    try:
        # Decode and decrypt
        decrypted_bytes = cipher_suite.decrypt(encrypted_text.encode())
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        logger.debug(f"Decrypted text: {decrypted_text}")
        return decrypted_text
    except Exception as e:
        logger.error(f"Decryption failed. Error details: {e}")
        logger.debug(f"Type of encrypted_text: {type(encrypted_text)}")
        logger.debug(f"Encrypted text content: {encrypted_text}")
        return None
    
for encrypted in encrypted_texts:
    decrypted_text = decrypt_text(encrypted)
    if decrypted_text is not None:
        logger.info(f"Decrypted: {decrypted_text}")
    else:
        logger.error("Decryption failed")
    
decrypted_text = decrypt_text(encrypted_texts[0])
if decrypted_text is not None:
    logger.info(f"Decrypted: {decrypted_text}")

# Add the parent directory to sys.path to import modules correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    logger.warning(f"Project root not in sys.path: {project_root}")
else:
    logger.info(f"Project root found in sys.path: {project_root}")
logger.info("Current working directory: %s", os.getcwd())
logger.info("sys.path: %s", sys.path)

try:
    from server.api_handler.api_services import preprocess_text, send_to_google_nlp_api, parse_api_response, extract_sentiment_score, extract_keywords
    logging.info("Imports successful.")
except ModuleNotFoundError as e:
    logging.error("ModuleNotFoundError: %s", e)
    raise

#Loading environment variables and verifying their setup.
load_dotenv()
credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    logging.info("GOOGLE_APPLICATION_CREDENTIALS is set to: %s", credentials_path)
    if os.path.isfile(credentials_path):
        logging.info("The credentials file exists.")
    else:
        logging.warning("The credentials file does not exist.")
else:
    logging.warning("GOOGLE_APPLICATION_CREDENTIALS is not set")


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
    logger.debug(f"Preprocessed Text: {preprocessed}")
    
    mock_response = {
        "document_sentiment": {
            "score": 0.9,
            "magnitude": 1.2
        },
        "sentences": [
            {
                "text": {
                    "content": "Natural Language Processing with Python is super fun!!",
                    "begin_offset": -1
                },
                "sentiment": {
                    "score": 0.9,
                    "magnitude": 1.2
                }
            }
        ]
    }

    mocker.patch('server.api_handler.api_services.get_nlp_client', return_value=mocker.Mock(analyze_sentiment=lambda document: mock_response))
    logger.debug(f"Mock NLP Client Setup: {mock_response}")
    response = send_to_google_nlp_api(preprocessed)
    logger.debug(f"Response: {response}")
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
        logger.debug(f"Preprocessed Text: '{preprocessed}' for Original Text: '{text}'")
        response = send_to_google_nlp_api(preprocessed)
        parsed_response = parse_api_response(response)
        actual_score = extract_sentiment_score(parsed_response, preprocessed_text=preprocessed)
        logger.debug(f"Actual Score: {actual_score} for Preprocessed Text: '{preprocessed}'")
        assert actual_score == pytest.approx(expected_score, abs=0.1)

# config.py tests
def test_get_nlp_client():
    client = get_nlp_client()
    assert client is not None

# User.py tests
def test_mood_user_creation():
    mood_user = MoodUser(user_id="testuser", preferences={"theme": "dark"})
    assert mood_user.user_id == "testuser"
    assert mood_user.preferences["theme"] == "dark"

def test_user_password_hashing():
    user = User(username="testuser")
    user.set_password("password123")
    assert user.check_password("password123") is True
    assert user.check_password("wrongpassword") is False

# Tests the store_preferences method with mocking
def test_store_preferences(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    mood_user = MoodUser(user_id="testuser", preferences={"theme": "dark"})
    mood_user.store_preferences()
    mood_user.db.collection('users').document.assert_called_once_with(mood_user.user_id)
    mood_user.db.collection('users').document(mood_user.user_id).set.assert_called_once()


def test_analyze_mood(mocker):
    disable_socket()
    try:
        # Mocking functions to return expected values
        mock_preprocess_text = mocker.patch('server.api_handler.api_services.preprocess_text', return_value="preprocessed text")
        
        mock_response = {
            "document_sentiment": {
                "score": -0.8,
                "magnitude": 0.8
            },
            "sentences": [
                {
                    "text": {
                        "content": "I'm not happy with this service.",
                        "begin_offset": -1
                    },
                    "sentiment": {
                        "score": -0.8,
                        "magnitude": 0.8
                    }
                }
            ]
        }
        
        mock_send_to_google_nlp_api = mocker.patch('server.api_handler.api_services.send_to_google_nlp_api', return_value=mock_response)
        mock_parsed_response = {"score": -0.8, "magnitude": 0.8, "sentences": ["preprocessed text"]}
        mock_parse_api_response = mocker.patch('server.api_handler.api_services.parse_api_response', return_value=mock_parsed_response)
        mock_extract_sentiment_score = mocker.patch('server.api_handler.api_services.extract_sentiment_score', return_value=-0.8)
        mock_extract_keywords = mocker.patch('server.api_handler.api_services.extract_keywords', return_value=["feeling", "stressed", "today"])

        mood_user = MoodUser(user_id="testuser")
        mood_analysis = mood_user.analyze_mood("I am feeling very stressed out today")
        logger.debug(f"mood_analysis returned from analyze_mood: {mood_analysis}")
        assert "feeling" in mood_analysis['keywords']
        assert "stressed" in mood_analysis['keywords']
        assert "today" in mood_analysis['keywords']
    
    finally:
        enable_socket()
    
# Tests the store_mood_analysis method with mocking
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

# Tests the update_last_login method with mocking
def test_update_last_login(mocker):
    mocker.patch('google.cloud.firestore.Client', return_value=MagicMock())
    mood_user = MoodUser(user_id="testuser")
    mood_user.update_last_login()
    mood_user.db.collection('users').document.assert_called_once_with(mood_user.user_id)
    mood_user.db.collection('users').document(mood_user.user_id).update.assert_called_once_with({
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




@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        logger.debug("Application context established")
        yield app

@pytest.fixture
def client(app):
    logger.debug("Creating test client")
    return app.test_client()

def test_analyze_tasks_happy_path_positive(client, mocker):
    mock_mood_user = mocker.patch('server.models.MoodUser.analyze_mood', autospec=True)
    mock_mood_user.return_value = {'moodCategory': 'positive'}

    mock_store = mocker.patch('server.models.MoodUser.store_mood_analysis')
    mock_preprocess = mocker.patch('server.api_handler.api_services.preprocess_text',  side_effect=preprocess_text)
    
    mock_send_nlp = mocker.patch('server.api_handler.api_services.send_to_google_nlp_api', return_value={
        "documentSentiment": {
            "score": 0.9,
            "magnitude": 1.2
        },
        "sentences": [
            {
                "text": {
                    "content": "task 1",
                    "begin_offset": 0
                },
                "sentiment": {
                    "score": 0.9,
                    "magnitude": 1.2
                }
            }
        ]
    })

    mock_parse = mocker.patch('server.api_handler.api_services.parse_api_response', return_value={"sentimentScore": 0.9})
    mock_extract_sentiment = mocker.patch('server.api_handler.api_services.extract_sentiment_score', return_value=0.9)
    mock_extract_keywords = mocker.patch('server.api_handler.api_services.extract_keywords', return_value=["keyword1", "keyword2"])

    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}, {"description": "task 2"}]}
    response = client.post('/tasks/analyze_tasks', json={"user_id": "testuser", 'text': 'I am feeling great today!'})
    print(response)
    print(dir(response))    

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}. Response JSON: {response.json}"
    assert response.json == {
        "userMoodCategory": "positive",
        "recommendedTasks": [],
        "taskSentiments": [],
        "status": "success"
    }
    response_json = response.get_json()
    assert response_json, "Response JSON is empty"
    assert 'recommendedTasks' in response_json, "Key 'recommendedTasks' not found in response JSON"
    assert response_json.get('userMoodCategory') == 'positive'

    response = client.post('/analyze_tasks', json={"user_id": "testuser", 'text': 'I am feeling great today!'})

    mock_mood_user.assert_called_once_with(mocker.ANY, 'task 1 task 2')
    mock_store.assert_called_once()
    mock_preprocess.assert_called_once_with(data['tasks'][0]['description'])
    mock_send_nlp.assert_called_once_with("preprocessed task")
    mock_parse.assert_called_once()
    mock_extract_sentiment.assert_called_once()
    mock_extract_keywords.assert_called_once()


def test_analyze_tasks_happy_path_negative(client, mocker):
    mock_mood_user = mocker.patch('server.models.MoodUser.analyze_mood', autospec=True)
    mock_mood_user.return_value = {'moodCategory': 'negative'}

    mock_store = mocker.patch('server.models.MoodUser.store_mood_analysis')
    mock_preprocess = mocker.patch('server.api_handler.api_services.preprocess_text', return_value="preprocessed task")
    
    mock_send_nlp = mocker.patch('server.api_handler.api_services.send_to_google_nlp_api', return_value={
        "documentSentiment": {
            "score": 0.9,
            "magnitude": 1.2
        },
        "sentences": [
            {
                "text": {
                    "content": "task 1",
                    "begin_offset": 0
                },
                "sentiment": {
                    "score": 0.9,
                    "magnitude": 1.2
                }
            }
        ]
    })

    mock_parse = mocker.patch('server.api_handler.api_services.parse_api_response', return_value={"sentimentScore": 0.9})
    mock_extract_sentiment = mocker.patch('server.api_handler.api_services.extract_sentiment_score', return_value=0.9)
    mock_extract_keywords = mocker.patch('server.api_handler.api_services.extract_keywords', return_value=["keyword1", "keyword2"])

    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}, {"description": "task 2"}]}
    response = client.post('/tasks/analyze_tasks', json=data)

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}. Response JSON: {response.json}"
    response_json = response.json()
    assert response_json, "Response JSON is empty"
    assert 'recommendedTasks' in response_json, "Key 'recommendedTasks' not found in response JSON"
    assert response_json.get('userMoodCategory') == 'negative'
    
    mock_mood_user.assert_called_once_with("preprocessed task")
    mock_store.assert_called_once()
    logger.debug(f"Checking if preprocess_text was called with: {data['tasks'][0]['description']}")
    mock_preprocess.assert_called_once_with(data['tasks'][0]['description'])
    mock_send_nlp.assert_called_once_with("preprocessed task")
    mock_parse.assert_called_once()
    mock_extract_sentiment.assert_called_once()
    mock_extract_keywords.assert_called_once()

def test_analyze_tasks_happy_path_neutral(client, mocker):
    mock_mood_user = mocker.patch('server.models.MoodUser.analyze_mood', autospec=True)
    mock_mood_user.return_value = {'moodCategory': 'neutral'}

    mock_store = mocker.patch('server.models.MoodUser.store_mood_analysis')
    mock_preprocess = mocker.patch('server.api_handler.api_services.preprocess_text', return_value="preprocessed task")
    
    mock_send_nlp = mocker.patch('server.api_handler.api_services.send_to_google_nlp_api', return_value={
        "documentSentiment": {
            "score": 0.9,
            "magnitude": 1.2
        },
        "sentences": [
            {
                "text": {
                    "content": "task 1",
                    "begin_offset": 0
                },
                "sentiment": {
                    "score": 0.9,
                    "magnitude": 1.2
                }
            }
        ]
    })

    mock_parse = mocker.patch('server.api_handler.api_services.parse_api_response', return_value={"sentimentScore": 0.9})
    mock_extract_sentiment = mocker.patch('server.api_handler.api_services.extract_sentiment_score', return_value=0.9)
    mock_extract_keywords = mocker.patch('server.api_handler.api_services.extract_keywords', return_value=["keyword1", "keyword2"])

    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}, {"description": "task 2"}]}
    response = client.post('/tasks/analyze_tasks', json=data)

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}. Response JSON: {response.json}"
    response_json = response.json()
    assert response_json, "Response JSON is empty"
    assert 'recommendedTasks' in response_json, "Key 'recommendedTasks' not found in response JSON"
    assert response_json.get('userMoodCategory') == 'neutral'
    
    mock_mood_user.assert_called_once_with("preprocessed task")
    mock_store.assert_called_once()
    mock_preprocess.assert_called_once_with(data['tasks'][0]['description'])
    mock_send_nlp.assert_called_once_with("preprocessed task")
    mock_parse.assert_called_once()
    mock_extract_sentiment.assert_called_once()
    mock_extract_keywords.assert_called_once()


def test_analyze_tasks_exception_handling(client, mocker):
    mocker.patch('server.models.MoodUser.analyze_mood', side_effect=Exception("Something went wrong"))
    
    data = {"user_id": "testuser", "tasks": [{"description": "task 1"}]}
    logger.debug(f"Request data: {data}")
    response = client.post('/tasks/analyze_tasks', json=data)
    logger.debug(f"Response JSON: {response.get_json()}")
    logger.debug(f"Response Status Code: {response.status_code}")

    assert response.status_code == 400
    assert "error" in response.json
    assert response.json["error"] == "Something went wrong"

def test_compare_mood_with_tasks():
    task_sentiments = [
        {'task': {'description': 'Task 1'}, 'sentimentScore': 0.9, 'keywords': []},
        {'task': {'description': 'Task 2'}, 'sentimentScore': -0.5, 'keywords': []},
        {'task': {'description': 'Task 3'}, 'sentimentScore': 0.0, 'keywords': []},
    ]

    result = compare_mood_with_tasks('positive', task_sentiments)
    assert len(result) == 1
    assert result[0]['description'] == 'Task 1'

    result = compare_mood_with_tasks('negative', task_sentiments)
    assert len(result) == 1
    assert result[0]['description'] == 'Task 2'

    result = compare_mood_with_tasks('neutral', task_sentiments)
    assert len(result) == 1
    assert result[0]['description'] == 'Task 3'

def test_recommend_general_uplifting_tasks():
    tasks = recommend_general_uplifting_tasks()
    assert len(tasks) > 0
    assert isinstance(tasks, list)
    assert 'description' in tasks[0]
    
@patch('server.api.task_controller.cipher_suite.encrypt')
@patch('server.api.task_controller.firestore_client.collection')
def test_store_user_data_securely(mock_firestore_collection, mock_encrypt):
    # Set up the mock behavior
    mock_encrypt.side_effect = lambda x: f"encrypted_{x}"
    mock_doc = mock_firestore_collection.return_value.document
    mock_doc.return_value.set = MagicMock()

    # Call the function under test
    store_user_data_securely('test_collection', 'test_document', {'field1': 'value1', 'field2': 'value2'})

    # Debugging prints
    print("Firestore collection called with:", mock_firestore_collection.call_args)
    print("Document called with:", mock_doc.call_args)
    print("Set method called with:", mock_doc.return_value.set.call_args_list)
    print("Encrypt call count:", mock_encrypt.call_count)
    for call in mock_encrypt.call_args_list:
        print("Encrypt call args:", call)

    # Assertions
    # Check if encrypt was called twice
    assert mock_encrypt.call_count == 2, "Expected encrypt to be called twice"
    
    # Check if encrypt was called with the correct arguments
    expected_calls = [call(b'value1'), call(b'value2')]
    mock_encrypt.assert_has_calls(expected_calls, any_order=True)
    
    # Check if the firestore client and document methods were called correctly
    mock_firestore_collection.assert_called_once_with('test_collection')
    mock_doc.assert_called_once_with('test_document')
    
    # Ensure that 'set' was called with the correct encrypted data
    expected_encrypted_data = {
        'field1': 'encrypted_value1',
        'field2': 'encrypted_value2'
    }
    mock_doc.return_value.set.assert_called_once_with(expected_encrypted_data)
    
    # Additional tests
    # Test with missing fields
    with pytest.raises(ValueError, match="Both 'field1' and 'field2' must be present in data"):
        store_user_data_securely('test_collection', 'test_document', {'field1': 'value1'})
    
    # Test with missing fields in encrypted data
    with pytest.raises(ValueError, match="Encryption failed for some required fields"):
        store_user_data_securely('test_collection', 'test_document', {'field1': 'value1', 'field2': None})


@patch('server.api.task_controller.cipher_suite.decrypt')
@patch('server.api.task_controller.firestore_client.collection')
def test_retrieve_user_data_securely(mock_firestore_collection, mock_decrypt):
    mock_decrypt.side_effect = lambda x: f"decrypted_{x}"
    mock_doc = mock_firestore_collection.return_value.document
    mock_doc.return_value.get.return_value.exists = True
    mock_doc.return_value.get.return_value.to_dict.return_value = {'field1': 'encrypted_value1', 'field2': 'encrypted_value2'}

    result = retrieve_user_data_securely('test_collection', 'test_document')
    
    mock_firestore_collection.assert_called_once_with('test_collection')
    mock_doc.assert_called_once_with('test_document')
    assert result == {'field1': 'decrypted_encrypted_value1', 'field2': 'decrypted_encrypted_value2'}

@patch('server.api.task_controller.firestore_client.collection')
def test_retrieve_user_data_securely_document_not_found(mock_firestore_collection):
    mock_doc = mock_firestore_collection.return_value.document
    mock_doc.return_value.get.return_value.exists = False

    result = retrieve_user_data_securely('test_collection', 'test_document')

    assert result is None

@patch('server.api.task_controller.firestore_client.collection')
def test_delete_no_longer_needed_data(mock_firestore_collection):
    mock_doc = mock_firestore_collection.return_value.document
    mock_doc.return_value.delete = MagicMock()

    delete_no_longer_needed_data('test_collection', 'test_document')

    mock_firestore_collection.assert_called_once_with('test_collection')
    mock_doc.assert_called_once_with('test_document')
    mock_doc.return_value.delete.assert_called_once()

@patch('server.api.task_controller.cipher_suite.decrypt')
@patch('server.api.task_controller.firestore_client.collection')
def test_decrypt_data(mock_firestore_collection, mock_decrypt):
    mock_decrypt.side_effect = lambda x: b"decrypted_value"
    encrypted_data = b"encrypted_value"
    result = decrypt_data(encrypted_data)
    assert result == "decrypted_value"
    mock_decrypt.assert_called_once_with(encrypted_data)


def test_reorganize_tasks_based_on_mood_and_sentiment_positive(mocker):
    tasks = [
        {"description": "Task 1", "priority": 1},
        {"description": "Task 2", "priority": 3},
        {"description": "Task 3", "priority": 2}
    ]
    mood_score = 1.0  # Positive mood score

    # Mock sentiment analysis
    mock_analyze_sentiment = mocker.patch('server.api.task_controller.analyze_task_sentiment')
    mock_analyze_sentiment.side_effect = lambda text: 0.5  # Example sentiment score

    expected_result = [
        {"description": "Task 2", "priority": 3, "sentiment_score": 0.5},
        {"description": "Task 3", "priority": 2, "sentiment_score": 0.5},
        {"description": "Task 1", "priority": 1, "sentiment_score": 0.5}
    ]
    assert reorganize_tasks_based_on_mood_and_sentiment(tasks, mood_score) == expected_result


    def test_reorganize_tasks_based_on_mood_and_sentiment_negative(mocker):
        tasks = [
            {"description": "Task 1", "priority": 1},
            {"description": "Task 2", "priority": 3},
            {"description": "Task 3", "priority": 2}
        ]
        mood_score = -1.0  # Negative mood score

        # Mock sentiment analysis
        mock_analyze_sentiment = mocker.patch('server.api.task_controller.analyze_task_sentiment')
        mock_analyze_sentiment.side_effect = lambda text: -0.5  # Example sentiment score

        expected_result = [
            {"description": "Task 1", "priority": 1, "sentiment_score": -0.5},
            {"description": "Task 3", "priority": 2, "sentiment_score": -0.5},
            {"description": "Task 2", "priority": 3, "sentiment_score": -0.5}
        ]
        assert reorganize_tasks_based_on_mood_and_sentiment(tasks, mood_score) == expected_result


def test_reorganize_tasks_based_on_mood_and_sentiment_neutral(mocker):
    tasks = [
        {"description": "Task 1", "priority": 1},
        {"description": "Task 2", "priority": 3},
        {"description": "Task 3", "priority": 2}
    ]
    mood_score = 0.0  # Neutral mood score

    # Mock sentiment analysis
    mock_analyze_sentiment = mocker.patch('server.api.task_controller.analyze_task_sentiment')
    mock_analyze_sentiment.side_effect = lambda text: 0.0  # Neutral sentiment score

    expected_result = [
        {"description": "Task 2", "priority": 3, "sentiment_score": 0.0},
        {"description": "Task 3", "priority": 2, "sentiment_score": 0.0},
        {"description": "Task 1", "priority": 1, "sentiment_score": 0.0}
    ]
    assert reorganize_tasks_based_on_mood_and_sentiment(tasks, mood_score) == expected_result

