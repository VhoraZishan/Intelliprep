from fastapi import APIRouter

router = APIRouter()

@router.get("/question/{index}")
def get_question(index: int):
    return {"question_index": index}
