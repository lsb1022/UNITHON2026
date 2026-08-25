from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import thumbnails
from .api import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # 썸네일용 Chromium 이 떠 있으면 같이 내린다. 안 내리면 프로세스가 안 죽는다.
    await thumbnails.shutdown()

app = FastAPI(title="AI 페르소나 UX 테스트 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5180"],  # Vite 개발 서버
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
