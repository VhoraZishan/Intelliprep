from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from uuid import uuid4
from datetime import datetime

from app.db import get_connection
from app.test_engine.generator import generate_question_ids

router = APIRouter()

@router.post("/start")
def start_test():
    session_id = str(uuid4())
    question_ids = generate_question_ids()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO sessions (id, status, start_time, question_ids)
        VALUES (%s, %s, %s, %s);
        """,
        (session_id, "IN_PROGRESS", datetime.utcnow(), question_ids),
    )

    conn.commit()
    cur.close()
    conn.close()

    response = RedirectResponse("/question-list", status_code=303)
    response.set_cookie("session_id", session_id, httponly=True)
    return response
