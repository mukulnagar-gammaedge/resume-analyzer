from fastapi import FastAPI
from app.api.routes import router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="AI Resume Analyzer")
app.include_router(router)
