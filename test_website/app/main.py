from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.db import get_connection, put_connection
from app.routes import start, question, question_list, submit
from datetime import datetime

app = FastAPI(title="IntelliPrep Test Website")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def home(request: Request):
    session_id = request.cookies.get("session_id")
    reason = request.query_params.get("reason")

    if session_id:
        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT status, expires_at
                FROM sessions
                WHERE id = %s;
                """,
                (session_id,),
            )
            row = cur.fetchone()

        finally:
            cur.close()
            put_connection(conn)

        if row:
            status, expires_at = row
            now = datetime.utcnow()

            # Active session → resume test
            if status == "IN_PROGRESS" and expires_at > now:
                return RedirectResponse("/question-list", status_code=303)

        # Invalid / expired / completed session → clear cookie
        response = templates.TemplateResponse(
            "start.html",
            {"request": request, "reason": reason},
        )
        response.delete_cookie("session_id")
        response.headers["Cache-Control"] = "no-store"
        return response

    # No session cookie
    return templates.TemplateResponse(
        "start.html",
        {"request": request, "reason": reason},
    )


app.include_router(start.router)
app.include_router(question.router)
app.include_router(question_list.router)
app.include_router(submit.router)
