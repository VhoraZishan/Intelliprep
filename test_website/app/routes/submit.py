from fastapi import APIRouter

router = APIRouter()

@router.post("/submit")
def submit_test():
    return {"status": "submitted"}
