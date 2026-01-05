from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime
from app.db import get_connection, put_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/question-list")
def question_list(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse("/?reason=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()

    try:
        # Fetch session ONCE
        cur.execute(
            """
            SELECT status, expires_at, question_ids
            FROM sessions
            WHERE id = %s;
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/?reason=invalid_session", status_code=303)

        status, expires_at, question_ids = row

        # Expiry handling
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
        put_connection(conn)

    # Precompute id → index map (O(n))
    index_map = {qid: idx for idx, qid in enumerate(question_ids)}

    attempted_indexes = {
        index_map[qid]
        for qid in attempted_ids
        if qid in index_map
    }

    response = templates.TemplateResponse(
        "question_list.html",
        {
            "request": request,
            "total_questions": len(question_ids),
            "attempted_indexes": attempted_indexes,
            "attempted_count": len(attempted_indexes),
            "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response
