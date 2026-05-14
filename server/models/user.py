from server.services.nlp import (
    preprocess_text, send_to_google_nlp_api, parse_api_response,
    extract_sentiment_score, extract_keywords
)
from google.cloud import firestore
import bcrypt
from cryptography.fernet import Fernet
import os
import logging

encryption_key = os.getenv('ENCRYPTION_KEY').encode()
cipher_suite = Fernet(encryption_key)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def encrypt_data(data):
    if isinstance(data, str):
        try:
            return cipher_suite.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    elif isinstance(data, dict):
        try:
            return {k: encrypt_data(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error encrypting dictionary data: {e}")
            raise
    else:
        return data


# Firestore MoodUser class for mood analysis and preferences
class MoodUser:
    def __init__(self, user_id, preferences=None, created_at=None, last_login=None, positive_threshold=0.25, negative_threshold=-0.25):
        self.user_id = user_id
        self.preferences = preferences or {}
        self.created_at = created_at
        self.last_login = last_login
        try:
            self.db = firestore.Client()
        except Exception as e:
            logger.warning(f"Firestore unavailable: {e}")
            self.db = None
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold

    def store_preferences(self):
        if not self.db:
            return
        try:
            encrypted_preferences = encrypt_data(self.preferences)
            self.db.collection('users').document(self.user_id).set({
                'preferences': encrypted_preferences,
                'createdAt': self.created_at,
                'lastLogin': self.last_login
            })
        except Exception as e:
            logger.error(f"An error occurred while storing user preferences: {e}")

    def analyze_mood(self, text):
        preprocessed_text = preprocess_text(text)
        response = send_to_google_nlp_api(preprocessed_text)
        parsed_response = parse_api_response(response)
        sentiment_score = extract_sentiment_score(parsed_response)
        keywords = extract_keywords(parsed_response)
        mood_category = self.classify_mood(sentiment_score)
        return {
            'inputText': text,
            'sentimentScore': sentiment_score,
            'keywords': keywords,
            'moodCategory': mood_category
        }

    def store_mood_analysis(self, mood_analysis, encrypt_func=encrypt_data):
        if not self.db:
            return
        try:
            encrypted_mood_analysis = {
                'inputText': encrypt_func(mood_analysis['inputText']),
                'sentimentScore': mood_analysis['sentimentScore'],
                'keywords': [encrypt_func(k) for k in mood_analysis['keywords']],
                'moodCategory': encrypt_func(mood_analysis['moodCategory']),
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            self.db.collection('moodAnalysis').document().set(encrypted_mood_analysis)
        except Exception as e:
            logger.error(f"An error occurred while storing mood analysis: {e}")

    def classify_mood(self, sentiment_score):
        if sentiment_score > self.positive_threshold:
            return 'positive'
        elif sentiment_score < self.negative_threshold:
            return 'negative'
        else:
            return 'neutral'
