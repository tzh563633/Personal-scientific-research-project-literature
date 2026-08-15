from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

from .config import settings
from .db import Base, engine
from .logging_setup import configure_logging
from .routers import agent, auth, code, commands, excel, jobs, journals, monitor, papers, reviews, setup, system
from . import models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    settings.storage_path
    configure_logging()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(setup.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(papers.router, prefix="/api/v1")
app.include_router(excel.router, prefix="/api/v1")
app.include_router(journals.router, prefix="/api/v1")
app.include_router(monitor.router, prefix="/api/v1")
app.include_router(code.router, prefix="/api/v1")
app.include_router(commands.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}
