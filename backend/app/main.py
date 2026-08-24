"""Spark Quest API.

Phase 0: infrastructure endpoints (/api/health)
Phase 1: course map endpoints (/api/levels, /api/levels/{id}/lessons)
Phase 2: dashboard endpoint (/api/dashboard)
Phase 3: lesson detail endpoint (/api/lessons/{id})
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import check_database_connection, init_db
from .routers import courses, dashboard, lessons, quizzes

logger = logging.getLogger("spark_quest")

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ok = check_database_connection()
    if ok:
        logger.info("SQLite connected and initialized successfully.")
    else:
        logger.error("SQLite connection check FAILED.")
    init_db()  # create tables + seed course data when empty
    yield


app = FastAPI(title="Spark Quest API", version="0.3.0", lifespan=lifespan)

# Frontend dev server (Vite) runs on port 6001.
# (6000 is blocked by Chromium as ERR_UNSAFE_PORT; 5173 also safe but user
# standardized on 6001.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:6001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses.router)
app.include_router(dashboard.router)
app.include_router(lessons.router)
app.include_router(quizzes.router)


@app.get("/api/health")
async def health():
    db_ok = check_database_connection()
    return {
        "app": "Spark Quest",
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
    }
