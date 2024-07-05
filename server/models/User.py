
# from server.api_services.api_services import (
#     preprocess_text, send_to_google_nlp_api, parse_api_response,
#     extract_sentiment_score, extract_keywords
# )

# from google.cloud import firestore

# db = firestore.Client()

# class User:
#     def __init__(self, user_id, preferences=None, created_at=None, last_login=None):
#         self.user_id = user_id
#         self.preferences = preferences or {}
#         self.created_at = created_at
#         self.last_login = last_login

#     def store_preferences(self):
#         """
#         Stores user preferences securely in Firestore
#         """
#         try:
#             db.collection('users').document(self.user_id).set({
#                 'preferences': self.preferences,
#                 'createdAt': self.created_at,
#                 'lastLogin': self.last_login
#             })
#             print(f"Preferences for user {self.user_id} successfully stored.")
#         except Exception as e:
#             print(f"An error occured while storing user preferences: {e}")
    
#     def analyze_mood(self, text):
#         """
#         Analyzes the user's mood based on input text
#         """
#         preprocessed_text = preprocess_text(text)
#         response = send_to_google_nlp_api(preprocessed_text)
#         parsed_response =  parse_api_response(response)
#         sentiment_score = extract_sentiment_score(parsed_response)
#         keywords = extract_keywords(parsed_response)
#         mood_category = self.classify_mood(sentiment_score)
#         return {
#             'inputText': text,
#             'sentimentScore': sentiment_score,
#             'keywords': keywords,
#             'moodCategory': mood_category
#         }
    
#     def store_mood_analysis(self, mood_analysis):
#         """
#         Stores the mood analysis result in Firestore
#         """
#         try:
#             db.collection('moodAnalysis').document().set({
#                 'userId': self.user_id,
#                 'inputText': mood_analysis['inputText'],
#                 'sentimentScore': mood_analysis['sentimentScore'],
#                 'keywords': mood_analysis['keywords'],
#                 'moodCategory': mood_analysis['moodCategory'],
#                 'timestamp': firestore.SERVER_TIMESTAMP
#             })
#             print(f"Mood analysis for user {self.user_id} successfully stored")
#         except Exception as e:
#             print(f"An error occured while storing mood analysis: {e}")
    
#     def update_last_login(self):
#         """
#         Updates the last login timestamp
#         """
#         self.last_login = firestore.SERVER_TIMESTAMP
#         try:
#             db.collection('users').document(self.user_id).update({
#                 'lastLogin': self.last_login
#             })
#             print(f"Last login for user {self.user_id} successfully updated.")
#         except Exception as e:
#             print(f"An error occured while updating last login: {e}")

#     def classify_mood(self, sentiment_score):
#         """
#         Classifies the user's mood based on the sentiment score
#         """
#         if sentiment_score > 0.3:
#             return 'positive'
#         elif sentiment_score < -0.3:
#             return 'negative'
#         else:
#             return 'neutral'
        
# if __name__ == "__main__":
#     user = User(
#         user_id="userId123",
#         preferences={
#             'preferredAtmosphere': 'calm',
#             'maxDistance': 10
#         },
#         created_at=firestore.SERVER_TIMESTAMP,
#         last_login=firestore.SERVER_TIMESTAMP
#     )

#     user.store_preferences()

#     mood_analysis = user.analyze_mood("I am feeling very stressed out today")
#     user.store_mood_analysis(mood_analysis)
#     user.update_last_login()
