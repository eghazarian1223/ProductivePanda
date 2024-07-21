
from flask import Blueprint, request, jsonify
from api_services.api_services import (preprocess_text, send_to_google_nlp_api, parse_api_response, extract_sentiment_score,extract_keywords)
import User as MoodUser
from google.cloud import firestore 

db = firestore.Client()
task_controller = Blueprint('task_controller', __name__)
@task_controller.route('/analyze_tasks', methods=['POST'])
def analyze_tasks():
    try:
        user_id = request.json.get('user_id', '')
        tasks = request.json.get('tasks', [])

        # Fetch user mood
        mood_user = MoodUser(user_id=user_id)
        combined_tasks_text = ' '.join(task['description'] for task in tasks)
        mood_analysis = mood_user.analyze_mood(combined_tasks_text)
        mood_user.store_mood_analysis(mood_analysis)
        user_mood_category = mood_analysis['moodCategory']

        # Preprocess tasks and analyze sentiment
        task_sentiments = []
        for task in tasks:
            preprocessed_task = preprocess_text(task['description'])
            response = send_to_google_nlp_api(preprocessed_task)
            parsed_response = parse_api_response(response)
            sentiment_score = extract_sentiment_score(parsed_response)
            task_sentiments.append({
                'task': task,
                'sentimentScore': sentiment_score,
                'keywords': extract_keywords(parsed_response)
            })
        matching_tasks = compare_mood_with_tasks(user_mood_category, task_sentiments)

        # Recommend tasks based on analysis
        if matching_tasks:
            recommended_tasks = matching_tasks
        else:
            recommended_tasks = recommend_general_uplifting_tasks()

        return jsonify({
            'message': 'Task analysis complete!',
            'recommended_tasks': recommended_tasks
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    

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

# Security and privacy functions
def store_user_data_securely(collection_name, document_id, data):
    try:
        db.collection(collection_name).document(document_id).set(data)
        print(f"Document {document_id} successfully written to {collection_name} collection.")
    except Exception as e:
        print(f"An error occurred while writing to Firestore: {e}")

def follow_data_minimization_principles(data, required_fields):
    minimized_data = {key: data[key] for key in required_fields if key in data}
    return minimized_data

def delete_no_longer_needed_data(collection_name, document_id):
    try:
        db.collection(collection_name).document(document_id).delete()
        print(f"Document {document_id} successfully deleted from {collection_name} collection.")
    except Exception as e:
        print(f"An error occurred while deleting from Firestore: {e}")

