from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.test_engine.state import SESSION_STORE
from app.db import get_connection
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/question-list")
def question_list(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=401, detail="Invalid session")

    state = SESSION_STORE[session_id]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT question_id FROM attempts
        WHERE session_id = %s;
        """,
        (session_id,),
    )

    attempted_ids = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()

    attempted_indexes = {
        state.question_ids.index(qid)
        for qid in attempted_ids
        if qid in state.question_ids
    }

    return templates.TemplateResponse(
        "question_list.html",
        {
            "request": request,
            "total_questions": len(state.question_ids),
            "attempted_indexes": attempted_indexes,
        },
    )