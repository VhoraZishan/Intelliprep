from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.db import get_connection
from app.routes import start, question, question_list, submit

app = FastAPI(title="IntelliPrep Test Website")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home(request: Request):
    session_id = request.cookies.get("session_id")

    if session_id:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM sessions WHERE id = %s AND status = 'IN_PROGRESS';",
            (session_id,),
        )
        valid = cur.fetchone()
        cur.close()
        conn.close()

        if valid:
            return RedirectResponse("/question-list", status_code=303)

    return templates.TemplateResponse("start.html", {"request": request})

app.include_router(start.router)
app.include_router(question.router)
app.include_router(question_list.router)
app.include_router(submit.router)
