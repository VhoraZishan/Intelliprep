from fastapi import FastAPI
from app.routes import start, question, submit

app = FastAPI(title="IntelliPrep Test Website")

app.include_router(start.router)
app.include_router(question.router)
app.include_router(submit.router)
