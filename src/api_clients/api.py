from openai import OpenAI
from google import genai
from src.settings import OPENAI_KEY
from src.settings import GOOGLE_KEY

openai_client = OpenAI(api_key=OPENAI_KEY)
gemini_client = genai.Client(api_key=GOOGLE_KEY)