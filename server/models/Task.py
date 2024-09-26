
from ..api_services.api_services import preprocess_text
from server.api_services.api_services import preprocess_text



class Task:
    def __init__(self, description):
        self.description = description

    def preprocess(self):
        return preprocess_text(self.description)
