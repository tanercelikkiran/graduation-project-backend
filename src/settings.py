from dotenv import load_dotenv
from os import getenv

# Load environment variables once
load_dotenv()

# Define variables for easy access
DATABASE_URL = getenv("DATABASE_URL")
OPENAI_KEY = getenv("OPENAI_KEY")
GOOGLE_KEY = getenv("GOOGLE_KEY")
TRANSLATE_KEY = getenv("TRANSLATE_KEY")
SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = "HS256"
CLIENT_ID = getenv("CLIENT_ID")
CLIENT_SECRET = getenv("CLIENT_SECRET")
ACCESS_TOKEN_EXPIRE_MINUTES = 3000
