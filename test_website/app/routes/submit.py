from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from datetime import datetime
from fastapi.templating import Jinja2Templates
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/submit")
def submit_test(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse("/?error=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM attempts WHERE session_id = %s AND is_correct = true;",
        (session_id,),
    )
    correct = cur.fetchone()[0]

    score = round((correct / 25) * 100, 2)

    cur.execute(
        """
        UPDATE sessions
        SET status = 'COMPLETED', end_time = %s
        WHERE id = %s;
        """,
        (datetime.utcnow(), session_id),
    )

    conn.commit()
    cur.close()
    conn.close()

    response = RedirectResponse(f"/complete?score={score}", status_code=303)
    response.delete_cookie("session_id")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/complete")
def complete(request: Request, score: float = Query(...)):
    return templates.TemplateResponse(
        "complete.html",
        {"request": request, "score_percent": score},
    )
