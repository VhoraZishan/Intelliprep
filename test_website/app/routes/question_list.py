from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/question-list")
def question_list(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RedirectResponse("/?reason=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Fetch session
        cur.execute(
            """
            SELECT status, expires_at, question_ids
            FROM sessions
            WHERE id = %s;
            """,
            (session_id,),
        )
        session = cur.fetchone()

        if not session:
            return RedirectResponse("/?reason=invalid_session", status_code=303)

        status, expires_at, question_ids = session
        now = datetime.utcnow()

        # Handle expired session
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

        # Handle non-active sessions
        if status == "COMPLETED":
            return RedirectResponse("/complete", status_code=303)

        if status != "IN_PROGRESS":
            return RedirectResponse("/?reason=invalid_session", status_code=303)

        # Fetch submitted attempts only
        cur.execute(
            """
            SELECT question_id
            FROM attempts
            WHERE session_id = %s
              AND submitted_at IS NOT NULL;
            """,
            (session_id,),
        )
        attempted_ids = {row[0] for row in cur.fetchall()}

    finally:
        cur.close()
        conn.close()

    # Map attempted question IDs to indexes
    attempted_indexes = {
        question_ids.index(qid)
        for qid in attempted_ids
        if qid in question_ids
    }

    response = templates.TemplateResponse(
        "question_list.html",
        {
            "request": request,
            "total_questions": len(question_ids),
            "attempted_indexes": attempted_indexes,
            "attempted_count": len(attempted_indexes),
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response
