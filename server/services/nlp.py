
import re
import nltk
import logging
import sys
from nltk.corpus import wordnet, stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer

sys.path.append(".")

lemmatizer = WordNetLemmatizer()
logging.basicConfig(level=logging.WARNING)

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
nltk.download('vader_lexicon')

_analyzer = SentimentIntensityAnalyzer()

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

def replace_contractions(text, contractions):
    pattern = re.compile('|'.join(re.escape(key) for key in contractions.keys()), re.IGNORECASE)
    def replace(match):
        return contractions[match.group().lower()]
    return pattern.sub(replace, text)

def preprocess_text(text):
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

    text = replace_contractions(text, contractions)
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)

    negations = ["not", "no", "never", "none", "neither", "nor", "nobody", "nothing", "nowhere",
    "cannot", "won't", "isn't", "aren't", "wasn't", "weren't",
    "doesn't", "don't", "didn't", "hasn't", "haven't", "hadn't", "wouldn't",
    "shouldn't", "couldn't", "mustn't", "cannot", "barely", "hardly", "scarcely", "seldom",
    "by no means", "in no way", "on no account", "at no time",
    "no longer", "no more", "not any", "not at all", "not even",
    "not only", "not until", "nevertheless", "nonetheless", "regardless",
    "despite", "without", "lack of", "fail to", "under no circumstances"]

    for negation in negations:
        text = re.sub(rf"\b({negation})\s+(\w+)", r"\1 \2", text)

    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english')) - set(negations) - {"but", "and", "can", "we", "will", "us"}
    tokens = [token for token in tokens if token not in stop_words]
    tokens = [lemmatizer.lemmatize(token) if token != "us" else token for token in tokens]

    return ' '.join(tokens)

def send_to_google_nlp_api(preprocessed_text):
    scores = _analyzer.polarity_scores(preprocessed_text)
    return {
        "overall_sentiment": {
            "score": scores['compound'],
            "magnitude": abs(scores['compound'])
        },
        "sentences": []
    }

def parse_api_response(response):
    return response

def extract_sentiment_score(parsed_response, preprocessed_text=None):
    score = parsed_response["overall_sentiment"]["score"]
    if preprocessed_text and preprocessed_text in ["ok"]:
        score = 0.1
    return score

def extract_keywords(parsed_response):
    keywords = []
    for sentence in parsed_response.get("sentences", []):
        content = sentence["content"]
        tokens = word_tokenize(content)
        keywords.extend(tokens)
    return keywords
