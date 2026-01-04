from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/question-list")
def question_list(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RedirectResponse("/?error=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    # Validate active session
    cur.execute(
        """
        SELECT question_ids
        FROM sessions
        WHERE id = %s AND status = 'IN_PROGRESS';
        """,
        (session_id,),
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return RedirectResponse("/?error=invalid_session", status_code=303)

    question_ids = row[0]

    # Fetch attempted questions
    cur.execute(
        "SELECT question_id FROM attempts WHERE session_id = %s;",
        (session_id,),
    )
    attempted_ids = {r[0] for r in cur.fetchall()}

    cur.close()
    conn.close()

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
