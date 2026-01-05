from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/submit")
def submit_test(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse("/?reason=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Fetch session
        cur.execute(
            """
            SELECT status, expires_at
            FROM sessions
            WHERE id = %s;
            """,
            (session_id,),
        )
        session = cur.fetchone()

        if not session:
            return RedirectResponse("/?reason=invalid_session", status_code=303)

        status, expires_at = session
        now = datetime.utcnow()

        # Handle expiry
        if status == "IN_PROGRESS" and expires_at <= now:
            cur.execute(
                """
                UPDATE sessions
                SET status = 'EXPIRED', end_time = %s
                WHERE id = %s;
                """,
                (now, session_id),
            )
            conn.commit()
            return RedirectResponse("/?reason=session_expired", status_code=303)

        # Reject non-active sessions
        if status != "IN_PROGRESS":
            return RedirectResponse("/complete", status_code=303)

        # Compute score from submitted attempts only
        cur.execute(
            """
            SELECT COUNT(*)
            FROM attempts
            WHERE session_id = %s AND is_correct = TRUE;
            """,
            (session_id,),
        )
        correct = cur.fetchone()[0]

        # NOTE: total questions is fixed at 25 for now
        score = round((correct / 25) * 100, 2)

        # Complete session (single transition)
        cur.execute(
            """
            UPDATE sessions
            SET status = 'COMPLETED', end_time = %s
            WHERE id = %s AND status = 'IN_PROGRESS';
            """,
            (now, session_id),
        )

        conn.commit()

    finally:
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
