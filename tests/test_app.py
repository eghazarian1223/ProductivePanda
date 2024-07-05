
# import sys
# import os
# import pytest


# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

<<<<<<< Updated upstream
# Import statements for the modules
from server.app import create_app 
# from server.api_services import preprocess_text, send_to_google_nlp_api
from server.api_services.api_services import preprocess_text, send_to_google_nlp_api
from server.config import get_nlp_client
from server.models.User import User
from server.models.Task import Task
=======
# # Import statements for the modules
# from server.app import create_app 
# from server.api_services.api_services import preprocess_text, send_to_google_nlp_api
# from server.config import get_nlp_client
# from server.models.User import User
# from server.models.Task import Task
>>>>>>> Stashed changes

# # app.py tests
# def test_app_initialization():
#     app = create_app()
#     assert app is not None

# def test_app_routes():
#     app = create_app()
#     client = app.test_client()
#     response = client.get('/')
#     assert response.status_code == 200

# # api_services.py tests
# def test_preprocess_text():
#     sample_text = "Natural Language Processing with Python is super fun!!"
#     preprocessed = preprocess_text(sample_text)
#     assert preprocessed is not None

# def test_send_to_google_nlp_api(mocker):
#     sample_text = "Natural Language Processing with Python is super fun!!"
#     preprocessed = preprocess_text(sample_text)
#     mock_response = mocker.Mock()
#     mock_response.document_sentiment.score = 0.9
#     mock_response.document_sentiment.magnitude = 1.2
#     mock_response.sentences = ["Natural Language Processing with Python is super fun!!"]
#     mocker.patch('server.api_services.get_nlp_client', return_value=mocker.Mock(analyze_sentiment=lambda x: mock_response))
#     response = send_to_google_nlp_api(preprocessed)
#     assert response is not None
#     assert response.document_sentiment.score == 0.9

# # config.py tests
# def test_get_nlp_client():
#     client = get_nlp_client()
#     assert client is not None

# User.py tests
# def test_user_creation():
#     user = User(user_id="testuser", preferences={"theme": "dark"})
#     assert user.user_id == "testuser"
#     assert user.preferences["theme"] == "dark"

# def test_user_password_hashing(mocker):
#     user = User(user_id="testuser")
#     user.set_password("password123")
#     assert user.check_password("password123") is True
#     assert user.check_password("wrongpassword") is False 

# # Task.py tests
# def test_task_creation():
#     task = Task(description="This is a Sample Task")
#     assert task.description == "This is a Sample Task" 

# def test_task_preprocess():
#     task = Task(description="Natural Language Processing with Python is super fun!!")
#     preprocessed = task.preprocess()
#     assert preprocessed is not None
