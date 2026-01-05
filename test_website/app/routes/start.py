from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from uuid import uuid4
from datetime import datetime, timedelta

from app.db import get_connection, put_connection
from app.test_engine.generator import generate_question_ids

router = APIRouter()

# Test duration (minutes)
TEST_DURATION_MINUTES = 45


@router.post("/start")
def start_test():
    session_id = str(uuid4())
    start_time = datetime.utcnow()
    expires_at = start_time + timedelta(minutes=TEST_DURATION_MINUTES)

    # Generate fixed question list
    question_ids = generate_question_ids()

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO sessions (
                id,
                status,
                start_time,
                expires_at,
                question_ids
            )
            VALUES (%s, 'IN_PROGRESS', %s, %s, %s);
            """,
            (session_id, start_time, expires_at, question_ids),
        )
        conn.commit()

    finally:
        cur.close()
        put_connection(conn)

    response = RedirectResponse("/question-list", status_code=303)
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=True,
        samesite="none",
    )
    return response
