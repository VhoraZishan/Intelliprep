from fastapi import FastAPI

from app.routes import start
from app.routes import question
from app.routes import submit
from app.routes import question_list

app = FastAPI(title="IntelliPrep Test Website")

app.include_router(start.router)
app.include_router(question.router)
app.include_router(question_list.router)
app.include_router(submit.router)
