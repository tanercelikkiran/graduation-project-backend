from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from src.settings import DATABASE_URL

client = MongoClient(DATABASE_URL, server_api=ServerApi("1"))
db = client["Edifica"]
user_table = db["User"]
pyramid_table = db["Pyramid"]
saved_sentence_table = db["SavedSentence"]
vocabulary_table = db["Vocabulary"]
writing_table = db["Writing"]
writing_answer_table = db["WritingAnswer"]
user_progress_table = db["UserProgress"]
user_events_table = db["UserEvent"]
vocabulary_statistics_table = db["VocabularyStatistic"]
translation_cache_table = db["TranslationCache"]

try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
