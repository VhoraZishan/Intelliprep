from fastapi import APIRouter, Request, HTTPException
from app.test_engine.state import SESSION_STORE
from app.db import get_connection
from datetime import datetime

router = APIRouter()

@router.get("/question/{index}")
def get_question(index: int, request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=401, detail="Invalid session")

    state = SESSION_STORE[session_id]

    if index < 0 or index >= len(state.question_ids):
        raise HTTPException(status_code=404, detail="Invalid question index")

    question_id = state.question_ids[index]

    # Start timing
    if index not in state.question_start_times:
        state.question_start_times[index] = datetime.utcnow()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, question_text, option_a, option_b, option_c, option_d
        FROM questions
        WHERE id = %s;
        """,
        (question_id,),
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "index": index,
        "question_id": row[0],
        "question_text": row[1],
        "options": {
            "A": row[2],
            "B": row[3],
            "C": row[4],
            "D": row[5],
        },
    }

@router.post("/question/{index}")
def submit_answer(index: int, request: Request, selected_option: str):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=401, detail="Invalid session")

    state = SESSION_STORE[session_id]

    if index < 0 or index >= len(state.question_ids):
        raise HTTPException(status_code=404, detail="Invalid question index")

    if index not in state.question_start_times:
        raise HTTPException(status_code=400, detail="Question not viewed yet")

    question_id = state.question_ids[index]

    start_time = state.question_start_times[index]
    time_taken_sec = int((datetime.utcnow() - start_time).total_seconds())

    conn = get_connection()
    cur = conn.cursor()

    # Attempt number = how many attempts already in this session + 1
    cur.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE session_id = %s;
        """,
        (session_id,),
    )
    attempt_number = cur.fetchone()[0] + 1

    # Prevent duplicate attempt for same question
    cur.execute(
        """
        SELECT 1 FROM attempts
        WHERE session_id = %s AND question_id = %s;
        """,
        (session_id, question_id),
    )

    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=409, detail="Answer already submitted")

    # Fetch correct option
    cur.execute(
        """
        SELECT correct_option FROM questions
        WHERE id = %s;
        """,
        (question_id,),
    )

    correct_option = cur.fetchone()[0]
    is_correct = selected_option.upper() == correct_option

    # Insert attempt
    cur.execute(
        """
        INSERT INTO attempts (
            session_id,
            question_id,
            selected_option,
            is_correct,
            time_taken_sec,
            attempt_number,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (
            session_id,
            question_id,
            selected_option.upper(),
            is_correct,
            time_taken_sec,
            attempt_number,
            datetime.utcnow(),
        ),
    )

    conn.commit()
    cur.close()
    conn.close()

    return {
        "index": index,
        "question_id": question_id,
        "selected_option": selected_option.upper(),
        "is_correct": is_correct,
        "time_taken_sec": time_taken_sec,
        "attempt_number": attempt_number,
    }
