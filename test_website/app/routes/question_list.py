from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from app.test_engine.state import SESSION_STORE
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/question-list")
def question_list(request: Request):
    session_id = request.cookies.get("session_id")

    # Validate session
    if not session_id or session_id not in SESSION_STORE:
        return RedirectResponse(
            url="/?error=invalid_session",
            status_code=303
        )


    state = SESSION_STORE[session_id]
    question_ids = state.question_ids

    # Fetch attempted questions from DB
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT question_id
        FROM attempts
        WHERE session_id = %s;
        """,
        (session_id,),
    )

    attempted_ids = {row[0] for row in cur.fetchall()}

    cur.close()
    conn.close()

    # Convert question IDs → indexes
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

    # Prevent browser caching (important)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
