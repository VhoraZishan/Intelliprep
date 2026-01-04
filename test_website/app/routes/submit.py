from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse
from datetime import datetime
from fastapi.templating import Jinja2Templates

from app.db import get_connection
from app.test_engine.state import SESSION_STORE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ----------------------
# SUBMIT TEST
# ----------------------
@router.post("/submit")
def submit_test(request: Request):
    session_id = request.cookies.get("session_id")

    # Validate session
    if not session_id or session_id not in SESSION_STORE:
        return RedirectResponse(
            url="/?error=invalid_session",
            status_code=303
        )


    conn = get_connection()
    cur = conn.cursor()

    # Calculate score
    cur.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE session_id = %s AND is_correct = true;
        """,
        (session_id,),
    )
    correct = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE session_id = %s;
        """,
        (session_id,),
    )
    attempted = cur.fetchone()[0]

    score_percent = round((correct / 25) * 100, 2)

    # Close session
    cur.execute(
        """
        UPDATE sessions
        SET status = %s, end_time = %s
        WHERE id = %s;
        """,
        ("COMPLETED", datetime.utcnow(), session_id),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Cleanup in-memory session
    SESSION_STORE.pop(session_id, None)

    # Redirect to completion page WITH score
    response = RedirectResponse(
        url=f"/complete?score={score_percent}",
        status_code=303
    )

    # Clear session cookie
    response.delete_cookie("session_id", path="/")

    # Prevent browser caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# ----------------------
# COMPLETE PAGE
# ----------------------
@router.get("/complete")
def test_complete(
    request: Request,
    score: float = Query(...)
):
    return templates.TemplateResponse(
        "complete.html",
        {
            "request": request,
            "score_percent": score
        }
    )
