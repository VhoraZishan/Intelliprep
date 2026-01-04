from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.test_engine.state import SESSION_STORE
from app.routes import start, question, question_list, submit

app = FastAPI(title="IntelliPrep Test Website")

# ----------------------
# Templates & Static
# ----------------------
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ----------------------
# ROOT ENTRY POINT
# ----------------------
@app.get("/")
def home(request: Request):
    session_id = request.cookies.get("session_id")

    # Resume active test
    if session_id and session_id in SESSION_STORE:
        response = RedirectResponse(
            url="/question-list",
            status_code=303
        )
    else:
        # Fresh start
        response = templates.TemplateResponse(
            "start.html",
            {"request": request}
        )

    # Prevent browser caching (important for back-button safety)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# ----------------------
# ROUTES
# ----------------------
app.include_router(start.router)
app.include_router(question.router)
app.include_router(question_list.router)
app.include_router(submit.router)
