"""
API FastAPI pour Agent Conversationnel Adjä
Patrimoine Béninois - Version Production
Endpoints : Chat, Historique, Reset, Health Check
"""

# =============================================================================
# IMPORTS
# =============================================================================

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import os
import uuid
from datetime import datetime
import threading
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

# Import de ton agent
from rag_conversational_agent_correction import BeninHeritageConversationalAgent

load_dotenv()

# =============================================================================
# DÉTECTION AUTOMATIQUE DE LANGUE
# =============================================================================

def detect_language(text: str, default: str = "fr") -> str:
    try:
        text_clean = text.strip()
        if len(text_clean) < 3:
            return default
        detected = detect(text_clean)
        return detected if detected in ["fr", "en"] else default
    except LangDetectException:
        return default
    except Exception:
        return default

# =============================================================================
# CONFIGURATION FASTAPI
# =============================================================================

app = FastAPI(
    title="Adjä API - Guide Culturel Béninois",
    description="API conversationnelle pour la découverte du patrimoine béninois",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# AGENT & SESSIONS
# =============================================================================

sessions: Dict[str, BeninHeritageConversationalAgent] = {}
default_agent: Optional[BeninHeritageConversationalAgent] = None

def init_agent_background():
    """Initialise l'agent global en arrière-plan (NON BLOQUANT)"""
    global default_agent
    try:
        print(" Initialisation de l'agent Adjä (background)...")
        default_agent = BeninHeritageConversationalAgent(
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            index_name=os.getenv("INDEX_NAME", "benin-heritage"),
            max_history=5
        )
        print(" Agent global prêt (background)")
    except Exception as e:
        print(f" Erreur initialisation agent: {e}")
        default_agent = None

@app.on_event("startup")
def startup_event():
    """Démarrage rapide compatible Render"""
    print(" API démarrée — port ouvert")
    thread = threading.Thread(target=init_agent_background, daemon=True)
    thread.start()

def get_or_create_agent(session_id: str) -> BeninHeritageConversationalAgent:
    if default_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Service en cours d'initialisation, veuillez réessayer"
        )
    if session_id not in sessions:
        sessions[session_id] = default_agent
    return sessions[session_id]

# =============================================================================
# MODÈLES
# =============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = None
    language: Optional[str] = Field(None, pattern="^(fr|en)$")
    verbose: bool = False

class ChatResponse(BaseModel):
    success: bool
    session_id: str
    query: str
    response: str
    images: List[str]
    sources: List[str]
    used_rag: bool
    intent: str
    language: str
    chunks_used: Optional[int]
    timestamp: str

class HistoryResponse(BaseModel):
    success: bool
    session_id: str
    history: List[Dict[str, str]]
    total_messages: int

class ResetResponse(BaseModel):
    success: bool
    session_id: str
    message: str

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API Adjä - Guide Culturel Béninois",
        "status": "operational",
        "version": "2.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy" if default_agent else "initializing",
        "agent_ready": default_agent is not None,
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(sessions)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    language = request.language or detect_language(request.message)
    agent = get_or_create_agent(session_id)

    result = agent.generate_response(
        query=request.message,
        language=language,
        verbose=request.verbose
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Erreur génération réponse")
        )

    return ChatResponse(
        success=True,
        session_id=session_id,
        query=result["query"],
        response=result["response"],
        images=result.get("images", []),
        sources=result.get("sources", []),
        used_rag=result.get("used_rag", False),
        intent=result.get("intent", "unknown"),
        language=language,
        chunks_used=result.get("chunks_used"),
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/history/{session_id}", response_model=HistoryResponse)
async def history(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session introuvable")
    agent = sessions[session_id]
    return HistoryResponse(
        success=True,
        session_id=session_id,
        history=agent.conversation_history,
        total_messages=len(agent.conversation_history)
    )

@app.delete("/reset/{session_id}", response_model=ResetResponse)
async def reset(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session introuvable")
    sessions[session_id].reset_conversation()
    return ResetResponse(
        success=True,
        session_id=session_id,
        message="Conversation réinitialisée"
    )

# =============================================================================
# GESTION D'ERREURS GLOBALE
# =============================================================================



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs global"""

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erreur interne du serveur",
            "details": str(exc),
            "path": str(request.url)
        }
    )

# =============================================================================
# DÉMARRAGE LOCAL UNIQUEMENT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Lancement local de l'API Adjä")
    print("📍 http://127.0.0.1:8000")
    print("📖 Docs : http://127.0.0.1:8000/docs")

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,   # OK en local uniquement
        log_level="info"
    )
