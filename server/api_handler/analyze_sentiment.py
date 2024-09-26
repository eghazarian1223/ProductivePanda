from google.cloud import language_v1
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/eghaz/Downloads/ProductivePandaDoingAgain/server/config/productivepandacredentials.json"

def analyze_sentiment(text_content):
    client = language_v1.LanguageServiceClient()
    document = {"content": text_content, "type_": language_v1.Document.Type.PLAIN_TEXT}
    response = client.analyze_sentiment(request={'document': document})
    print(f"Overall Sentiment: score = {response.document_sentiment.score}, magnitude = {response.document_sentiment.magnitude}")

    for sentence in response.sentences:
        print(f"Sentence: {sentence.text.content}")
        print(f"Sentiment: score = {sentence.sentiment.score}, magnitude = {sentence.sentiment.magnitude}")

    return response.document_sentiment.score

if __name__ == "__main__":
    texts_to_analyze = [
        "I'm not happy with this service.",
        "The movie was good, but the ending was not.",
        "I love it!",
        "It's ok.",
        "Terrible service, never coming back!"
    ]
    for text in texts_to_analyze:
        print(f"Analyzing: {text}")
        score = analyze_sentiment(text)
        print(f"Sentiment score: {score}\n")
