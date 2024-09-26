
import re
import nltk
import logging
import sys
from flask import request, jsonify
from nltk.corpus import wordnet, stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from google.cloud import firestore, language_v1
from cryptography.fernet import Fernet
import traceback 
import os

sys.path.append(".")
from server.config.config import get_nlp_client

db = firestore.Client()
encryption_key = os.getenv('ENCRYPTION_KEY').encode()
cipher_suite = Fernet(encryption_key)
lemmatizer = WordNetLemmatizer()
logging.basicConfig(level=logging.DEBUG)

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')

# Preprocessing functions
def to_lowercase(text):
    return text.lower()

def remove_punctuation(text):
    return re.sub(r'[^\w\s\'"]', '', text)

def tokenize_text(text):
    return word_tokenize(text)

def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

# Replace contractions
def replace_contractions(text, contractions):
    pattern = re.compile('|'.join(re.escape(key) for key in contractions.keys()), re.IGNORECASE)
    def replace(match):
        return contractions[match.group().lower()]
    return pattern.sub(replace, text)
  
def preprocess_text(text):
    print(f"preprocess_text called with: {text}")
    logging.debug(f"Original text: {text}")
    contractions = {
        "can't": "can not",
        "won't": "will not",
        "i'm": "i am",
        "you're": "you are",
        "he's": "he is",
        "she's": "she is",
        "it's": "it is",
        "we're": "we are",
        "they're": "they are",
        "i'll": "i will",
        "we'll": "we will",
        "you'll": "you will",
        "he'll": "he will",
        "she'll": "she will",
        "let's": "let us",
        "that's": "that is",
        "n't": " not",
        "'m": " am",
        "'re": " are",
        "'s": " is",
        "'ll": " will",
        "'d": " would",
        "'ve": " have",
        "there's": "there is",
        "who's": "who is",
        "she'd": "she would",
        "he'd": "he would",
        "they'd": "they would",
        "you'd": "you would",
        "ain't": "is not",
        "y'all": "you all",
        "we'd": "we would",
        "it'd": "it would"
    }

    # Step 1: Replace contractions
    text = replace_contractions(text, contractions)
    logging.debug(f"Text after contractions replacement: {text}")
    
    # Step 2: Convert to lowercase
    text = text.lower()
    logging.debug(f"Text after converting to lowercase: {text}")

    # Step 3: Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    logging.debug(f"Text after punctuation removal: {text}")

    # Step 4: Handle negations
    negations = ["not", "no", "never", "none", "neither", "nor", "nobody", "nothing", "nowhere", 
    "cannot", "won't", "isn't", "aren't", "wasn't", "weren't", 
    "doesn't", "don't", "didn't", "hasn't", "haven't", "hadn't", "wouldn't", 
    "shouldn't", "couldn't", "mustn't", "cannot", "barely", "hardly", "scarcely", "seldom", 
    "by no means", "in no way", "on no account", "at no time", 
    "no longer", "no more", "not any", "not at all", "not even", 
    "not only", "not until", "nevertheless", "nonetheless", "regardless", 
    "despite", "without", "lack of", "fail to", "under no circumstances"]

    for negation in negations:
        text = re.sub(rf"\b({negation})\s+(\w+)", r"\1 \2", text)  # Keep space instead of underscore
    logging.debug(f"Text after negation handling: {text}")

    # Step 6: Tokenize text
    tokens = word_tokenize(text)
    logging.debug(f"Tokens: {tokens}")

    # Step 6: Remove stop words, but keep key conjunctions like "but" and negation words
    stop_words = set(stopwords.words('english')) - set(negations) - {"but", "and", "can", "we", "will", "us"}
    tokens = [token for token in tokens if token not in stop_words]

    logging.debug(f"Tokens after stop word removal: {tokens}")

    # Step 8: Lemmatize tokens and ensure "us" isn't altered
    tokens = [lemmatizer.lemmatize(token) if token != "us" else token for token in tokens]
    logging.debug(f"Tokens after lemmatization: {tokens}")

    # Join tokens back into a single string
    preprocessed_text = ' '.join(tokens)
    logging.debug(f"Preprocessed text: {preprocessed_text}")
    return preprocessed_text

def remove_stop_words(tokens):
    stop_words = set(stopwords.words('english'))
    return [token for token in tokens if token not in stop_words]

def lemmatize_tokens(tokens):
    return [lemmatizer.lemmatize(token) for token in tokens]

def send_to_google_nlp_api(preprocessed_text):
    logging.debug(f"Sending text to Google NLP API: {preprocessed_text}")
    client = get_nlp_client()
    logging.debug(f"Google NLP client created: {client}")
    document = language_v1.Document(content=preprocessed_text, type_=language_v1.Document.Type.PLAIN_TEXT)
    try:
        response = client.analyze_sentiment(document=document)
        logging.debug(f"Google NLP API response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error analyzing sentiment: {e}")
        logging.error(traceback.format_exc())  # Log the stack trace
        raise ValueError(f"Error analyzing sentiment: {e}")


def parse_api_response(response):
    sentiment = response.document_sentiment
    sentences = [
        {
            "content": sentence.text.content,
            "sentiment": sentence.sentiment.score,
            "magnitude": sentence.sentiment.magnitude
        } for sentence in response.sentences if sentence.text.content
    ]
    overall_sentiment = {
        "score": sentiment.score,
        "magnitude": sentiment.magnitude
    }
    return {
        "overall_sentiment": overall_sentiment,
        "sentences": sentences
    }

def extract_sentiment_score(parsed_response, preprocessed_text=None):
    """Extract sentiment score from parsed response."""
    score = parsed_response["overall_sentiment"]["score"]
    # Custom logic for specific phrases
    if preprocessed_text and preprocessed_text in ["ok"]:
        score = 0.1
    return score


def extract_sentiment_magnitude(parsed_response):
    """Extract sentiment magnitude from parsed response."""
    return parsed_response["overall_sentiment"]["magnitude"]

def extract_keywords(parsed_response):
    """Extract keywords from parsed response."""
    keywords = []
    for sentence in parsed_response["sentences"]:
        content = sentence["content"]
        tokens = word_tokenize(content)
        keywords.extend(tokens)
    return keywords

# Middleware functions
def api_request_handler():
    try:
        data = request.get_json()
        return data
    except Exception as e:
        logging.error(f"Error in request data: {e}")
        return jsonify({"error": str(e)}), 400
    
# Security and privacy functions
def encrypt_data(data):
    if isinstance(data, str):
        return cipher_suite.encrypt(data.encode()).decode('utf-8')
    return data

def decrypt_data(data):
    if isinstance(data, str):
        return cipher_suite.decrypt(data.encode('utf-8')).decode('utf-8')
    return data

def retrieve_user_data_securely(collection_name, document_id):
    try:
        doc = db.collection(collection_name).document(document_id).get()
        if doc.exists:
            decrypted_data = {k: decrypt_data(v) for k, v in doc.to_dict().items()}
            logging.info(f"Document {document_id} successfully retrieved and decrypted.")
            return decrypted_data
        else:
            logging.error(f"No document found for ID {document_id} in {collection_name} collection.")
            return None
    except Exception as e:
        logging.error(f"An error occurred while retrieving data from Firestore: {e}")
        return None

def store_user_data_securely(collection_name, document_id, data):
    try:
        encrypted_data = {k: encrypt_data(v) for k, v in data.items()}
        db.collection(collection_name).document(document_id).set(encrypted_data)
        logging.info(f"Document {document_id} successfully written to {collection_name} collection.")
    except Exception as e:
        logging.error(f"An error occurred while writing to Firestore: {e}")

def follow_data_minimization_principles(data, required_fields):
    """Minimize data to only required fields."""
    return {key: data[key] for key in required_fields if key in data}

def delete_no_longer_needed_data(collection_name, document_id):
    try:
        db.collection(collection_name).document(document_id).delete()
        logging.info(f"Document {document_id} successfully deleted from {collection_name} collection.")
    except Exception as e:
        logging.error(f"An error occurred while deleting from Firestore: {e}")


if __name__ == "__main__":
    sample_text = "Natural Language Processing with Python is fun!"
    preprocessed_text = preprocess_text(sample_text)
    sentiment_response = send_to_google_nlp_api(preprocessed_text)
    print(sentiment_response)
    print("Sentiment Score:", extract_sentiment_score(sentiment_response))
    print("Keywords:", extract_keywords(sentiment_response))

    # Example usage for mood analysis

    mood_data = {
        "userId": "userId123",
        "inputText": "I am feeling very stressed out today.",
        "sentimentScore": -0.8,
        "keywords": ["stressed", "today"],
        "moodCategory": "overwhelmed",
        "timestamp": firestore.SERVER_TIMESTAMP
    }

    # Store mood analysis data securely
    store_user_data_securely("moodAnalysis", "moodAnalysisId123", mood_data)

    # Follow data minimization principles
    required_fields = ["userId", "inputText", "sentimentScore", "keywords", "moodCategory", "timestamp"]
    minimized_mood_data = follow_data_minimization_principles(mood_data, required_fields)
    print(minimized_mood_data)

    # Delete mood analysis data when no longer needed
    delete_no_longer_needed_data("moodAnalysis", "moodAnalysisId123")
