from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, knowledge, documents

app = FastAPI(title="Smart Campus RAG", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(documents.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "smart-campus-rag"}
