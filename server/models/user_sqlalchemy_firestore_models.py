# During refactoring, it might be a good idea to change the file name that recognizes you're using two databases
# Code in here has both the SQLAlchemy database login stuff and Firestore mood reorganization stuff

# SQLAlchemy User Class (User): Manages usernames and passwords.

# Firestore MoodUser Class (MoodUser): Handles mood analysis and stores preferences using Firestore.

from server.api_handler.api_services import (
    preprocess_text, send_to_google_nlp_api, parse_api_response,
    extract_sentiment_score, extract_keywords
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from google.cloud import firestore
import bcrypt
from cryptography.fernet import Fernet
import os
import logging

db = SQLAlchemy()
encryption_key = os.getenv('ENCRYPTION_KEY').encode()
cipher_suite = Fernet(encryption_key)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def encrypt_data(data):
    """Encrypt data with basic logging."""
    if isinstance(data, str):
        try:
            logger.debug(f"Encrypting string data: {data}")
            encrypted_data = cipher_suite.encrypt(data.encode())
            encrypted_text = encrypted_data.decode()
            logger.debug(f"Encrypted data: {encrypted_text}")
            return encrypted_text
        except Exception as e:
            logger.error(f"Error encrypting string data '{data}': {e}")
            raise
    elif isinstance(data, dict):
        try:
            logger.debug(f"Encrypting dictionary data: {data}")
            encrypted_dict = {k: encrypt_data(v) for k, v in data.items()}
            return encrypted_dict
        except Exception as e:
            logger.error(f"Error encrypting dictionary data '{data}': {e}")
            raise
    else:
        logger.debug(f"Data of unsupported type: {data}")
        return data

# SQLAlchemy User model for authentication
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

# Firestore MoodUser class for mood analysis and preferences
class MoodUser:
    def __init__(self, user_id, preferences=None, created_at=None, last_login=None, positive_threshold=0.25, negative_threshold=-0.25):
        self.user_id = user_id
        self.preferences = preferences or {}
        self.created_at = created_at
        self.last_login = last_login
        self.db = firestore.Client()
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold

    def decrypt_data(self, data):
        """Decrypt data with detailed logging."""
        logger.debug(f"Data before decryption: {data}")
        logger.debug(f"Type of data before decryption: {type(data)}")
        
        if isinstance(data, str):
            try:
                # Assuming the data is base64 encoded
                logger.debug(f"Attempting to decrypt string data.")
                decrypted_data = cipher_suite.decrypt(data.encode()).decode('utf-8')
                logger.debug(f"Decrypted data: {decrypted_data}")
                return decrypted_data
            except Exception as e:
                logger.error(f"Decryption error: {e}")
                raise
        elif isinstance(data, dict):
            try:
                logger.debug(f"Decrypting dictionary data.")
                decrypted_dict = {k: self.decrypt_data(v) for k, v in data.items()}
                return decrypted_dict
            except Exception as e:
                logger.error(f"Error decrypting dictionary data: {e}")
                raise
        else:
            logger.debug(f"Data type not supported for decryption: {type(data)}")
            return data

    def store_preferences(self):
        """
        Stores user preferences securely in Firestore
        """
        try:
            encrypted_preferences = encrypt_data(self.preferences)
            self.db.collection('users').document(self.user_id).set({
                'preferences': encrypted_preferences,
                'createdAt': self.created_at,
                'lastLogin': self.last_login
            })
            print(f"Preferences for user {self.user_id} successfully stored.")
        except Exception as e:
            print(f"An error occurred while storing user preferences: {e}")

    def analyze_mood(self, text):
        """
        Analyzes the user's mood based on input text
        """
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
        """
        Stores the mood analysis result in Firestore
        """
        try:
            encrypted_mood_analysis = {
                'inputText': encrypt_func(mood_analysis['inputText']),
                'sentimentScore': mood_analysis['sentimentScore'],
                'keywords': [encrypt_func(k) for k in mood_analysis['keywords']],
                'moodCategory': encrypt_func(mood_analysis['moodCategory']),
                'timestamp': firestore.SERVER_TIMESTAMP                         
            }

            self.db.collection('moodAnalysis').document().set(encrypted_mood_analysis)
            print(f"Mood analysis for user {self.user_id} successfully stored")
        except Exception as e:
            print(f"An error occurred while storing mood analysis: {e}")

    def retrieve_preferences(self):
        """
        Retrieves and decrypts user preferences from Firestore
        """
        try:
            doc = self.db.collection('users').document(self.user_id).get()
            if doc.exists:
                decrypted_preferences = self.decrypt_data(doc.to_dict().get('preferences', {}))
                return decrypted_preferences
            else:
                print(f"No preferences found for user {self.user_id}")
                return None
        except Exception as e:
            print(f"An error occurred while retrieving user preferences: {e}")
            return None

    def update_last_login(self):
        """
        Updates the last login timestamp
        """
        self.last_login = firestore.SERVER_TIMESTAMP
        try:
            self.db.collection('users').document(self.user_id).update({
                'lastLogin': self.last_login
            })
            print(f"Last login for user {self.user_id} successfully updated.")
        except Exception as e:
            print(f"An error occurred while updating last login: {e}")

    def classify_mood(self, sentiment_score):
        if sentiment_score > self.positive_threshold:
            return 'positive'
        elif sentiment_score < self.negative_threshold:
            return 'negative'
        else:
            return 'neutral'

if __name__ == "__main__":
    user = MoodUser(
        user_id="userId123",
        preferences={
            'preferredAtmosphere': 'calm',
            'maxDistance': 10
        },
        created_at=firestore.SERVER_TIMESTAMP,
        last_login=firestore.SERVER_TIMESTAMP
    )

    user.store_preferences()

    mood_analysis = user.analyze_mood("I am feeling very stressed out today")
    user.store_mood_analysis(mood_analysis)
    user.update_last_login()
