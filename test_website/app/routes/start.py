from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def landing_page():
    return {"status": "landing"}
