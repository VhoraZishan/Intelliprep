from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime
from app.db import get_connection, put_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/question/{index}")
def get_question(index: int, request: Request):
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

        # Handle expiry
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

        if index < 0 or index >= len(question_ids):
            raise HTTPException(status_code=404)

        question_id = question_ids[index]

        # Fetch question
        cur.execute(
            """
            SELECT question_text, option_a, option_b, option_c, option_d
            FROM questions
            WHERE id = %s;
            """,
            (question_id,),
        )
        question = cur.fetchone()
        if not question:
            raise HTTPException(status_code=404)

        # Fetch / create attempt (idempotent)
        cur.execute(
            """
            SELECT selected_option, submitted_at
            FROM attempts
            WHERE session_id = %s AND question_id = %s;
            """,
            (session_id, question_id),
        )
        attempt = cur.fetchone()

        if not attempt:
            cur.execute(
                """
                INSERT INTO attempts (session_id, question_id, started_at)
                VALUES (%s, %s, %s);
                """,
                (session_id, question_id, now),
            )
            conn.commit()
            is_attempted = False
            selected_option = None
        else:
            selected_option, submitted_at = attempt
            is_attempted = submitted_at is not None

        options = {
            "A": question[1],
            "B": question[2],
            "C": question[3],
            "D": question[4],
        }

    finally:
        cur.close()
        put_connection(conn)

    response = templates.TemplateResponse(
        "question.html",
        {
            "request": request,
            "index": index,
            "total_questions": len(question_ids),
            "question_text": question[0],
            "options": options,
            "is_attempted": is_attempted,
            "selected_option": selected_option,
            "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/question/{index}")
def submit_answer(index: int, request: Request, selected_option: str = Form(...)):
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

        if status != "IN_PROGRESS":
            return RedirectResponse("/question-list", status_code=303)

        if index < 0 or index >= len(question_ids):
            return RedirectResponse("/question-list", status_code=303)

        question_id = question_ids[index]

        # Fetch attempt
        cur.execute(
            """
            SELECT started_at, submitted_at
            FROM attempts
            WHERE session_id = %s AND question_id = %s;
            """,
            (session_id, question_id),
        )
        attempt = cur.fetchone()
        if not attempt:
            return RedirectResponse("/question-list", status_code=303)

        started_at, submitted_at = attempt
        if submitted_at is not None:
            return RedirectResponse("/question-list", status_code=303)

        time_taken = max(0, int((now - started_at).total_seconds()))

        # Faster attempt_number computation
        cur.execute(
            """
            SELECT COALESCE(MAX(attempt_number), 0)
            FROM attempts
            WHERE session_id = %s;
            """,
            (session_id,),
        )
        attempt_number = cur.fetchone()[0] + 1

        cur.execute(
            "SELECT correct_option FROM questions WHERE id = %s;",
            (question_id,),
        )
        correct_option = cur.fetchone()[0]

        cur.execute(
            """
            UPDATE attempts
            SET selected_option = %s,
                is_correct = %s,
                time_taken_sec = %s,
                attempt_number = %s,
                submitted_at = %s
            WHERE session_id = %s AND question_id = %s;
            """,
            (
                selected_option.upper(),
                selected_option.upper() == correct_option,
                time_taken,
                attempt_number,
                now,
                session_id,
                question_id,
            ),
        )

        conn.commit()

    finally:
        cur.close()
        put_connection(conn)

    next_index = index + 1
    if next_index < len(question_ids):
        return RedirectResponse(f"/question/{next_index}", status_code=303)

    return RedirectResponse("/question-list", status_code=303)
