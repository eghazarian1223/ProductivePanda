
from flask import Blueprint, request, jsonify
from server.api_handler.analyze_sentiment import analyze_sentiment
from server.models.user_sqlalchemy_firestore_models import MoodUser
from google.cloud import firestore, language_v1
from cryptography.fernet import Fernet 
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
encryption_key = os.getenv('ENCRYPTION_KEY')
print(f"Loaded encryption key: {encryption_key}") 
encryption_key = os.getenv('ENCRYPTION_KEY').encode()
print(f"Encoded encryption key: {encryption_key}") 
cipher_suite = Fernet(encryption_key)

firestore_client = firestore.Client()

def analyze_task_sentiment(task_text):
    """
    Analyzes the sentiment of a given task description using Google Cloud NLP API.
    """
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=task_text, type_=language_v1.Document.Type.PLAIN_TEXT)
    
    try:
        sentiment = client.analyze_sentiment(request={"document": document}).document_sentiment
        return sentiment.score
    except Exception as e:
        return 0  
    
def reorganize_tasks_based_on_mood_and_sentiment(tasks, mood_score):
    """
    Reorganizes tasks based on mood score and sentiment of each task.
    Positive mood score -> prioritize tasks with higher priority and positive sentiment.
    Negative mood score -> prioritize tasks with lower priority and negative sentiment.
    """
    if not tasks:
        return tasks  

    # Analyze sentiment for each task
    for task in tasks:
        task['sentiment_score'] = analyze_task_sentiment(task['description'])

    if mood_score > 0:
        # Positive mood score: prioritize higher priority and positive sentiment
        tasks_sorted = sorted(
            tasks,
            key=lambda x: (x.get('priority', 0), x.get('sentiment_score', 0)),
            reverse=True
        )
    elif mood_score < 0:
        # Negative mood score: prioritize lower priority and negative sentiment
        tasks_sorted = sorted(
            tasks,
            key=lambda x: (x.get('priority', 0), -x.get('sentiment_score', 0)),
            reverse=False
        )
    else:
        # Neutral mood score: prioritize tasks with priority regardless of sentiment
        tasks_sorted = sorted(
            tasks,
            key=lambda x: x.get('priority', 0),
            reverse=True
        )
    return tasks_sorted

task_controller = Blueprint('task_controller', __name__)
@task_controller.route('/analyze_tasks', methods=['POST'])
def analyze_tasks():
    try:
        request_data = request.get_json()
        if not request_data:
            raise ValueError("No data provided")

        user_id = request_data.get('user_id', '')
        tasks = request_data.get('tasks', [])

        if not isinstance(tasks, list):
            raise ValueError("Tasks should be a list")

        if not user_id:
            raise ValueError("User ID is required")

        logger.debug(f"Received request JSON: {request_data}")
        logger.debug(f"Received user_id: {user_id}")
        logger.debug(f"Received tasks: {tasks}")

        # Fetch user mood
        mood_user = MoodUser(user_id=user_id)
        combined_tasks_text = ' '.join(task.get('description', '') for task in tasks if 'description' in task)
        sentiment_score = analyze_sentiment(combined_tasks_text)
        user_mood_category = mood_user.classify_mood(sentiment_score)
        reorganized_tasks = reorganize_tasks_based_on_mood_and_sentiment(tasks, sentiment_score)
        
        # Analyze sentiment for each task individually
        task_sentiments = [{"task": task.get("description", ""), "sentimentScore": analyze_task_sentiment(task.get("description", ""))} for task in tasks]

        return jsonify({
            "userMoodCategory": user_mood_category,
            "recommendedTasks": reorganized_tasks,
            "taskSentiments": task_sentiments,
            "status": "success"
        })

    except ValueError as ve:
        logger.error(f"ValueError: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Exception: {e}")
        return jsonify({"error": "An error occurred while processing the request."}), 500

    
def recommend_tasks_based_on_analysis(task_sentiments):
    """
    Recommends tasks based on their sentiment scores.
    
    Parameters:
    - task_sentiments (list of dict): List of tasks with their sentiment scores and other details.
    
    Returns:
    - list of dict: Recommended tasks with sentiment scores greater than 0.5.
    """
 
    if not isinstance(task_sentiments, list):
        raise ValueError("task_sentiments should be a list")
    if any(not isinstance(task, dict) or 'sentimentScore' not in task for task in task_sentiments):
        raise ValueError("Each task must be a dictionary with a 'sentimentScore' key")
    recommended_tasks = [task for task in task_sentiments if task.get('sentimentScore', 0) > 0.5]
    return recommended_tasks

def compare_mood_with_tasks(user_mood_category, task_sentiments):
    matching_tasks = []
    for task in task_sentiments:
        if task['sentimentScore'] > 0 and user_mood_category == 'positive':
            matching_tasks.append(task['task'])
        elif task['sentimentScore'] < 0 and user_mood_category == 'negative':
            matching_tasks.append(task['task'])
        elif task['sentimentScore'] == 0 and user_mood_category == 'neutral':
            matching_tasks.append(task['task'])
    return matching_tasks

def recommend_general_uplifting_tasks():
    # Example of general uplifting tasks
    return [
        {'description': 'Go for a walk in the park'},
        {'description': 'Read a book'},
        {'description': 'Listen to your favorite music'}
    ]

def encrypt_data(data):
    if isinstance(data, str):
        return cipher_suite.encrypt(data.encode()).decode()
    return data

def store_user_data_securely(collection_name, document_id, data):
    try:
        fields_to_encrypt = ['field1', 'field2']
        
        # Ensure all required fields are present
        if not all(field in data for field in fields_to_encrypt):
            raise ValueError("Both 'field1' and 'field2' must be present in data")

        # Encrypt only specified fields
        encrypted_data = {k: cipher_suite.encrypt(v.encode()).decode() 
                          for k, v in data.items() if k in fields_to_encrypt}
        
        # Ensure all required fields are encrypted
        if not all(field in encrypted_data for field in fields_to_encrypt):
            raise ValueError("Encryption failed for some required fields")

        firestore_client.collection(collection_name).document(document_id).set(encrypted_data)
        print(f"Document {document_id} successfully written to {collection_name} collection.")
    except Exception as e:
        print(f"An error occurred while writing to Firestore: {e}")


def decrypt_data(encrypted_data):
    """Decrypt data after retrieving it"""
    if isinstance(encrypted_data, str):
        encrypted_data = encrypted_data.encode()
    try:
        decrypted = cipher_suite.decrypt(encrypted_data)
        if isinstance(decrypted, bytes):
            decrypted_text = decrypted.decode('utf-8')
        else:
            decrypted_text = decrypted
        return decrypted_text
    except Exception as e:
        logger.error(f"Error in decrypt_data: {e}")
        raise

def retrieve_user_data_securely(collection_name, document_id):
    try:
        doc = firestore_client.collection(collection_name).document(document_id).get()
        if doc.exists:
            decrypted_data = {k: decrypt_data(v) for k, v in doc.to_dict().items()}
            print(f"Document {document_id} successfully retrieved and decrypted.")
            return decrypted_data
        else:
            print(f"No document found for ID {document_id} in {collection_name} collection.")
            return None
    except Exception as e:
        print(f"An error occurred while retrieving data from Firestore: {e}")
        return None

def delete_no_longer_needed_data(collection_name, document_id):
    try:
        firestore_client.collection(collection_name).document(document_id).delete()
        print(f"Document {document_id} successfully deleted from {collection_name} collection.")
    except Exception as e:
        print(f"An error occurred while deleting from Firestore: {e}")

