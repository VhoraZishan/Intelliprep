from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/question/{index}")
def get_question(index: int, request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse("/?error=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

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

    if index < 0 or index >= len(question_ids):
        raise HTTPException(status_code=404)

    question_id = question_ids[index]

    cur.execute(
        """
        SELECT question_text, option_a, option_b, option_c, option_d
        FROM questions WHERE id = %s;
        """,
        (question_id,),
    )
    question = cur.fetchone()

    cur.execute(
        """
        SELECT selected_option
        FROM attempts
        WHERE session_id = %s AND question_id = %s;
        """,
        (session_id, question_id),
    )
    attempt = cur.fetchone()

    cur.close()
    conn.close()

    if not question:
        raise HTTPException(status_code=404)

    response = templates.TemplateResponse(
        "question.html",
        {
            "request": request,
            "index": index,
            "total_questions": len(question_ids),
            "question_text": question[0],
            "options": {
                "A": question[1],
                "B": question[2],
                "C": question[3],
                "D": question[4],
            },
            "is_attempted": attempt is not None,
            "selected_option": attempt[0] if attempt else None,
        },
    )

    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/question/{index}")
def submit_answer(index: int, request: Request, selected_option: str = Form(...)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse("/?error=invalid_session", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT question_ids FROM sessions WHERE id = %s AND status = 'IN_PROGRESS';",
        (session_id,),
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return RedirectResponse("/?error=invalid_session", status_code=303)

    question_ids = row[0]
    question_id = question_ids[index]

    cur.execute(
        "SELECT 1 FROM attempts WHERE session_id = %s AND question_id = %s;",
        (session_id, question_id),
    )
    if cur.fetchone():
        cur.close()
        conn.close()
        return RedirectResponse("/question-list", status_code=303)

    cur.execute(
        "SELECT correct_option FROM questions WHERE id = %s;",
        (question_id,),
    )
    correct = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO attempts
        (session_id, question_id, selected_option, is_correct, time_taken_sec, attempt_number, created_at)
        VALUES (%s, %s, %s, %s, 0, 1, %s);
        """,
        (session_id, question_id, selected_option.upper(), selected_option.upper() == correct, datetime.utcnow()),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Redirect to next question if exists, else question list
    next_index = index + 1

    if next_index < len(question_ids):
        return RedirectResponse(
            url=f"/question/{next_index}",
            status_code=303
        )
    else:
        return RedirectResponse(
            url="/question-list",
            status_code=303
        )


