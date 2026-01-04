from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime

from app.test_engine.state import SESSION_STORE
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ----------------------
# GET QUESTION
# ----------------------
@router.get("/question/{index}")
def get_question(index: int, request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=401, detail="Invalid session")

    state = SESSION_STORE[session_id]

    if index < 0 or index >= len(state.question_ids):
        raise HTTPException(status_code=404, detail="Invalid question index")

    question_id = state.question_ids[index]

    conn = get_connection()
    cur = conn.cursor()

    # ⏱️ Start timing once
    if index not in state.question_start_times:
        state.question_start_times[index] = datetime.utcnow()

    # 📄 Fetch question
    cur.execute(
        """
        SELECT question_text, option_a, option_b, option_c, option_d
        FROM questions
        WHERE id = %s;
        """,
        (question_id,),
    )
    row = cur.fetchone()

    if row is None:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")

    # ✅ Check if already attempted
    cur.execute(
        """
        SELECT selected_option
        FROM attempts
        WHERE session_id = %s AND question_id = %s;
        """,
        (session_id, question_id),
    )
    attempt_row = cur.fetchone()

    cur.close()
    conn.close()

    response = templates.TemplateResponse(
        "question.html",
        {
            "request": request,
            "index": index,
            "total_questions": len(state.question_ids),
            "question_text": row[0],
            "options": {
                "A": row[1],
                "B": row[2],
                "C": row[3],
                "D": row[4],
            },
            "is_attempted": attempt_row is not None,
            "selected_option": attempt_row[0] if attempt_row else None,
        },
    )

    # 🔒 Prevent browser caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# ----------------------
# SUBMIT ANSWER
# ----------------------
@router.post("/question/{index}")
def submit_answer(
    index: int,
    request: Request,
    selected_option: str = Form(...)
):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        return RedirectResponse(
            url="/?error=invalid_session",
            status_code=303
        )


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

    # Prevent duplicate submission
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
        return RedirectResponse("/question-list", status_code=303)

    # Attempt number
    cur.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE session_id = %s;
        """,
        (session_id,),
    )
    attempt_number = cur.fetchone()[0] + 1

    # Correct option
    cur.execute(
        """
        SELECT correct_option
        FROM questions
        WHERE id = %s;
        """,
        (question_id,),
    )
    correct_option = cur.fetchone()[0]

    is_correct = selected_option.upper() == correct_option

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

    
    return RedirectResponse(url=f"/question/{index}",status_code=303)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
