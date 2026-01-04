from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from app.db import get_connection
from app.test_engine.state import SESSION_STORE

router = APIRouter()


@router.post("/submit")
def submit_test(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=401, detail="Invalid session")

    conn = get_connection()
    cur = conn.cursor()

    # Calculate score
    cur.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE session_id = %s AND is_correct = true;
        """,
        (session_id,),
    )
    correct = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE session_id = %s;
        """,
        (session_id,),
    )
    attempted = cur.fetchone()[0]

    # Close session
    cur.execute(
        """
        UPDATE sessions
        SET status = %s, end_time = %s
        WHERE id = %s;
        """,
        ("COMPLETED", datetime.utcnow(), session_id),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Cleanup in-memory session
    SESSION_STORE.pop(session_id, None)

    return {
        "session_id": session_id,
        "attempted": attempted,
        "correct": correct,
        "total": 25,
        "score_percent": round((correct / 25) * 100, 2),
    }
