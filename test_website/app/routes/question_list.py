from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.test_engine.state import SESSION_STORE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/question-list")
def question_list(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=401, detail="Invalid session")

    state = SESSION_STORE[session_id]

    return templates.TemplateResponse(
        "question_list.html",
        {
            "request": request,
            "total_questions": len(state.question_ids),
        },
    )
