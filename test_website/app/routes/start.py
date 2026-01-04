from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from uuid import uuid4
from datetime import datetime

from app.db import get_connection
from app.test_engine.state import SessionState, SESSION_STORE
from app.test_engine.generator import generate_question_ids

router = APIRouter()


@router.post("/start")
def start_test():
    session_id = str(uuid4())

    # Generate test
    question_ids = generate_question_ids()

    # Persist session
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO sessions (id, status, start_time)
        VALUES (%s, %s, %s);
        """,
        (session_id, "IN_PROGRESS", datetime.utcnow()),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Store in-memory state
    SESSION_STORE[session_id] = SessionState(
        session_id=session_id,
        question_ids=question_ids
    )

    # Redirect to question list (PRG pattern)
    response = RedirectResponse(
        url="/question-list",
        status_code=303
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        path="/"
    )

    # Prevent browser caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
