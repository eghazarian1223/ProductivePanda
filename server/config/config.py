import os
from google.cloud import language_v1, firestore
from google.oauth2 import service_account

def get_nlp_client():
    # Load credentials from the environment variable
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        return language_v1.LanguageServiceClient(credentials=credentials)
    else:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

def get_firestore_client():
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        return firestore.Client(credentials=credentials)
    else:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment is not set")

