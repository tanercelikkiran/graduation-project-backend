from fastapi import FastAPI
from src.routes import (
    authentication,
    leaderboard,
    user,
    user_progress,
    vocabulary,
    statistics,
    xp,
    pyramid,
    suggested_module,
    weekly_progress,
    saved_sentences,
    writing,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from src.settings import SECRET_KEY


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
""" app.include_router(google_auth.router)   """
app.include_router(vocabulary.router)
app.include_router(authentication.router)
app.include_router(statistics.router)
app.include_router(xp.router)
app.include_router(user_progress.router)
app.include_router(leaderboard.router)
app.include_router(pyramid.router)
app.include_router(suggested_module.router)
app.include_router(weekly_progress.router)
app.include_router(saved_sentences.router)
app.include_router(writing.router)
