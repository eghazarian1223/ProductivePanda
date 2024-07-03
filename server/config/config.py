
import os
from google.cloud import language_v1
from google.oauth2 import service_account
# Make sure to put whatever is meant to be in google_places_config.py into this file, and then delete that one


def get_nlp_client():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "server/config/productivepandacredentials.json" 
    return language_v1.LanguageServiceClient


