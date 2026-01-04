from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.test_engine.state import SESSION_STORE
from app.routes import start, question, submit, question_list

app = FastAPI(title="IntelliPrep Test Website")

# Templates & static
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ----------------------
# ROOT ENTRY POINT
# ----------------------
@app.get("/")
def home(request: Request):
    session_id = request.cookies.get("session_id")

    # Active session → resume test
    if session_id and session_id in SESSION_STORE:
        return RedirectResponse("/question-list")

    # No session → start page
    return templates.TemplateResponse(
        "start.html",
        {"request": request}
    )


# ----------------------
# ROUTES
# ----------------------
app.include_router(start.router)
app.include_router(question.router)
app.include_router(question_list.router)
app.include_router(submit.router)
