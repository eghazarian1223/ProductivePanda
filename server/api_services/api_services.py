# import string
# import nltk
# from flask import request, jsonify
# from nltk.corpus import stopwords
# from nltk.tokenize import word_tokenize
# from nltk.stem import WordNetLemmatizer
# import sys
# sys.path.append(".")
# from server.config.config import get_nlp_client
# from google.cloud import firestore, language_v1


# db = firestore.Client()

# # Download necessary NLTK data
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')

# # Preprocessing functions
# def to_lowercase(text): # Write a couple of helpful comments throughout (but don't overdo it) as you learn  
#     return text.lower() # Ask for simple example for each function to clarify if needed 

# def remove_punctuation(text):
#     return text.translate(str.maketrans('', '', string.punctuation))

# def tokenize_text(text):
#     return word_tokenize(text)

# def remove_stop_words(tokens):
#     stop_words = set(stopwords.words('english'))
#     return [token for token in tokens if token not in stop_words]

# def lemmatize_tokens(tokens):
#     lemmatizer = WordNetLemmatizer()
#     return [lemmatizer.lemmatize(token) for token in tokens]

# def preprocess_text(text):
#     text = to_lowercase(text)
#     text = remove_punctuation(text)
#     tokens = tokenize_text(text)
#     tokens = remove_stop_words(tokens)
#     tokens = lemmatize_tokens(tokens)
#     return ' '.join(tokens)

# # API interaction functions
# def send_to_google_nlp_api(preprocessed_text):
#     client = get_nlp_client()
#     document = language_v1.Document(content=preprocessed_text, type_=language_v1.Document.Type.PLAIN_TEXT)
#     response = client.analyze_sentiment(document=document)
#     return response


# def parse_api_response(response):
#     sentiment = response.document_sentiment
#     return {
#         "score": sentiment.score,
#         "magnitude": sentiment.magnitude,
#         "sentences": [sentence.text.content for sentence in response.sentences]
#     }

# def extract_sentiment_score(parsed_response):
#     return parsed_response["score"]

# def extract_keywords(parsed_response):
#     return parsed_response["sentences"]

# # Middleware functions
# def api_request_handler():
#     try:
#         data = request.get_json()
#         return data
#     except Exception as e:
#         return jsonify({"error": str(e)}), 400
    
# # Security and privacy functions


# def store_user_data_securely(collection_name, document_id, data):
#     try:
#         db.collection(collection_name).document(document_id).set(data)
#         print(f"Document {document_id} successfully written to {collection_name} collection.")
#     except Exception as e:
#         print(f"An error occurred while writing to Firestore: {e}") 

# def follow_data_minimization_principles(data, required_fields):
#     minimized_data = {key: data[key] for key in required_fields if key in data}
#     return minimized_data

# def delete_no_longer_needed_data(collection_name, document_id):
#     try:
#         db.collection(collection_name).document(document_id).delete()
#         print(f"Document {document_id} successfully deleted from {collection_name} collection.")
#     except Exception as e:
#         print(f"An error occurred while deleting from Firestore: {e}")


# if __name__ == "__main__":
#     sample_text = "Natural Language Processing with Python is fun!"
#     preprocessed_text = preprocess_text(sample_text)
#     sentiment_response = send_to_google_nlp_api(preprocessed_text)
#     print(sentiment_response)
#     print("Sentiment Score:", extract_sentiment_score(sentiment_response))
#     print("Keywords:", extract_keywords(sentiment_response))

#     # Example usage for mood analysis

#     mood_data = {
#         "userId": "userId123",
#         "inputText": "I am feeling very stressed out today.",
#         "sentimentScore": -0.8,
#         "keywords": ["stressed", "today"],
#         "moodCategory": "overwhelmed",
#         "timestamp": firestore.SERVER_TIMESTAMP
#     }

#     # Store mood analysis data securely
#     store_user_data_securely("moodAnalysis", "moodAnalysisId123", mood_data)

#     # Follow data minimization principles
#     required_fields = ["userId", "inputText", "sentimentScore", "keywords", "moodCategory", "timestamp"]
#     minimized_mood_data = follow_data_minimization_principles(mood_data, required_fields)
#     print(minimized_mood_data)

#     # Delete mood analysis data when no longer needed
#     delete_no_longer_needed_data("moodAnalysis", "moodAnalysisId123")

