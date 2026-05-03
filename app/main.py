from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.api.lesson_feedback import router as lessons_router
from app.api.korean_sign import router as korean_router
# from app.api.simulation import router as simulation_router

app = FastAPI()
app.include_router(lessons_router, prefix="/api/lessons")
app.include_router(korean_router, prefix="/api/korean")
# app.include_router(simulation_router, prefix="/api", tags=["Simulation"])

@app.get("/record", response_class=HTMLResponse)
async def serve_record_page():
    html_file = Path(__file__).resolve().parent.parent / "static" / "record.html"
    return html_file.read_text(encoding="utf-8")

@app.get("/check", response_class=HTMLResponse)
async def serve_check_page():
    html_file = Path(__file__).resolve().parent.parent / "static" / "check.html"
    return html_file.read_text(encoding="utf-8")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
