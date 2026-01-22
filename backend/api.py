"""
API FastAPI pour Agent Conversationnel Adjä
Patrimoine Béninois - Version Production
Endpoints : Chat, Historique, Reset, Health Check
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

# Import de ton agent
from rag_conversational_agent_correction import BeninHeritageConversationalAgent

load_dotenv()

# =============================================================================
# DÉTECTION AUTOMATIQUE DE LANGUE
# =============================================================================

def detect_language(text: str, default: str = "fr") -> str:
    """
    Détecte automatiquement la langue d'un texte
    
    Args:
        text: Texte à analyser
        default: Langue par défaut si détection échoue (défaut: "fr")
        
    Returns:
        Code langue ('fr' ou 'en')
        
    Examples:
        >>> detect_language("Bonjour, comment allez-vous ?")
        'fr'
        >>> detect_language("Hello, how are you?")
        'en'
        >>> detect_language("Ghézo ?")
        'fr'
    """
    try:
        # Nettoyer le texte
        text_clean = text.strip()
        
        # Si texte trop court (< 3 caractères), utiliser default
        if len(text_clean) < 3:
            return default
        
        # Détection avec langdetect
        detected = detect(text_clean)
        
        # Mapper vers nos langues supportées
        if detected in ['fr', 'en']:
            return detected
        else:
            # Langue non supportée (ex: 'es', 'de') → utiliser default
            print(f"⚠️ Langue détectée '{detected}' non supportée, utilisation de '{default}'")
            return default
            
    except LangDetectException as e:
        # Erreur de détection (texte trop court, ambigu) → utiliser default
        print(f"⚠️ Impossible de détecter la langue: {e}, utilisation de '{default}'")
        return default
    except Exception as e:
        # Autre erreur → utiliser default
        print(f"❌ Erreur détection langue: {e}, utilisation de '{default}'")
        return default

# =============================================================================
# CONFIGURATION
# =============================================================================

app = FastAPI(
    title="Adjä API - Guide Culturel Béninois",
    description="API conversationnelle pour la découverte du patrimoine béninois",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (pour React Native et web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production : spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# GESTION DES SESSIONS
# =============================================================================

# Stockage en mémoire des agents par session
# En production : Utiliser Redis ou une base de données
sessions: Dict[str, BeninHeritageConversationalAgent] = {}

# Agent global initialisé au démarrage (évite le rechargement à chaque requête)
print("🚀 Initialisation de l'agent global au démarrage...")
default_agent = BeninHeritageConversationalAgent(
    pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    gemini_api_key=os.getenv("GEMINI_API_KEY"),
    index_name=os.getenv("INDEX_NAME", "benin-heritage"),
    max_history=5
)
print("✅ Agent global prêt\n")

def get_or_create_agent(session_id: str) -> BeninHeritageConversationalAgent:
    """Récupère ou crée un agent pour une session"""
    if session_id not in sessions:
        sessions[session_id] = default_agent
    return sessions[session_id]

def cleanup_old_sessions():
    """Nettoie les sessions inactives (à appeler périodiquement)"""
    # TODO : Implémenter avec timestamp et limite de sessions
    pass

# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class ChatRequest(BaseModel):
    """Requête de chat avec détection automatique de langue"""
    message: str = Field(..., min_length=1, max_length=500, description="Message de l'utilisateur")
    session_id: Optional[str] = Field(None, description="ID de session (auto-généré si absent)")
    language: Optional[str] = Field(
        None, 
        pattern="^(fr|en)$", 
        description="Langue souhaitée (optionnel, auto-détectée si null/absent)"
    )
    verbose: bool = Field(False, description="Activer les logs détaillés")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qui est le roi Ghézo ?",
                "session_id": "user-123-abc",
                "language": None,  # null = détection auto
                "verbose": False
            }
        }

class ChatResponse(BaseModel):
    """Réponse de chat"""
    success: bool
    session_id: str
    query: str
    response: str
    images: List[str]
    sources: List[str]
    used_rag: bool
    intent: str
    language: str
    chunks_used: Optional[int] = None
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "user-123-abc",
                "query": "Qui est le roi Ghézo ?",
                "response": "Ah, le roi Ghézo ! Quelle excellente question...",
                "images": ["palais_ghezo.jpg", "symbole_ghezo.jpg"],
                "sources": ["Wikipédia FR - Ghézo"],
                "used_rag": True,
                "intent": "heritage_question",
                "language": "fr",
                "chunks_used": 2,
                "timestamp": "2025-01-15T10:30:00"
            }
        }

class HistoryResponse(BaseModel):
    """Historique de conversation"""
    success: bool
    session_id: str
    history: List[Dict[str, str]]
    total_messages: int

class ResetResponse(BaseModel):
    """Confirmation de reset"""
    success: bool
    session_id: str
    message: str

class ErrorResponse(BaseModel):
    """Réponse d'erreur"""
    success: bool = False
    error: str
    details: Optional[str] = None

# =============================================================================
# ENDPOINTS PRINCIPAUX
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur l'API Adjä - Guide Culturel Béninois",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "chat": "/chat",
            "history": "/history/{session_id}",
            "reset": "/reset/{session_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Vérifie la santé de l'API"""
    try:
        # Vérifier les variables d'environnement
        pinecone_ok = bool(os.getenv("PINECONE_API_KEY"))
        gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
        
        return {
            "status": "healthy" if (pinecone_ok and gemini_ok) else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "pinecone": "connected" if pinecone_ok else "missing_key",
                "gemini": "connected" if gemini_ok else "missing_key"
            },
            "active_sessions": len(sessions)
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Endpoint principal de conversation avec Adjä
    
    **Détection automatique de langue** : Si `language` est null/absent, 
    la langue est détectée automatiquement à partir du message.
    
    - **message**: Question de l'utilisateur
    - **session_id**: ID de session (optionnel, auto-généré si absent)
    - **language**: Langue souhaitée (optionnel: null = auto, "fr" = force français, "en" = force anglais)
    - **verbose**: Logs détaillés (pour debug)
    
    Returns:
        ChatResponse avec la réponse d'Adjä + métadonnées (dont la langue utilisée)
    """
    try:
        # Générer ou récupérer session_id
        session_id = request.session_id or str(uuid.uuid4())
        
        # 🆕 DÉTECTION AUTOMATIQUE DE LA LANGUE (si non spécifiée)
        if request.language is None:
            detected_language = detect_language(request.message, default="fr")
            if request.verbose:
                print(f"🌍 Langue auto-détectée: {detected_language} pour '{request.message[:50]}...'")
        else:
            detected_language = request.language
            if request.verbose:
                print(f"🌍 Langue spécifiée manuellement: {detected_language}")
        
        # Récupérer ou créer l'agent
        agent = get_or_create_agent(session_id)
        
        # Générer la réponse avec la langue détectée/spécifiée
        result = agent.generate_response(
            query=request.message,
            language=detected_language,  # ← Langue auto-détectée ou forcée
            verbose=request.verbose
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Erreur inconnue lors de la génération')
            )
        
        # Construire la réponse
        return ChatResponse(
            success=True,
            session_id=session_id,
            query=result['query'],
            response=result['response'],
            images=result.get('images', []),
            sources=result.get('sources', []),
            used_rag=result.get('used_rag', False),
            intent=result.get('intent', 'unknown'),
            language=detected_language,  # ← Retourne la langue utilisée (importante pour l'UI)
            chunks_used=result.get('chunks_used'),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )

@app.get("/history/{session_id}", response_model=HistoryResponse, tags=["Chat"])
async def get_history(session_id: str):
    """
    Récupère l'historique de conversation d'une session
    
    - **session_id**: ID de la session
    
    Returns:
        HistoryResponse avec l'historique complet
    """
    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' introuvable"
            )
        
        agent = sessions[session_id]
        
        return HistoryResponse(
            success=True,
            session_id=session_id,
            history=agent.conversation_history,
            total_messages=len(agent.conversation_history)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )

@app.delete("/reset/{session_id}", response_model=ResetResponse, tags=["Chat"])
async def reset_conversation(session_id: str):
    """
    Réinitialise la conversation d'une session
    
    - **session_id**: ID de la session
    
    Returns:
        ResetResponse confirmant la réinitialisation
    """
    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' introuvable"
            )
        
        agent = sessions[session_id]
        agent.reset_conversation()
        
        return ResetResponse(
            success=True,
            session_id=session_id,
            message="Conversation réinitialisée avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la réinitialisation: {str(e)}"
        )

@app.delete("/session/{session_id}", tags=["Session Management"])
async def delete_session(session_id: str):
    """
    Supprime complètement une session (libère la mémoire)
    
    - **session_id**: ID de la session
    """
    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' introuvable"
            )
        
        del sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session supprimée avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )

# =============================================================================
# ENDPOINTS AVANCÉS (OPTIONNEL)
# =============================================================================

@app.get("/sessions", tags=["Session Management"])
async def list_sessions():
    """Liste toutes les sessions actives"""
    return {
        "success": True,
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "messages_count": len(agent.conversation_history),
                "current_topic": agent.current_topic,
                "current_pole": agent.current_pole
            }
            for sid, agent in sessions.items()
        ]
    }

@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """
    Version streaming de l'endpoint chat (pour réponses progressives)
    TODO: Implémenter le streaming Gemini
    """
    return JSONResponse(
        status_code=501,
        content={
            "success": False,
            "error": "Streaming non encore implémenté",
            "message": "Utilisez l'endpoint /chat pour le moment"
        }
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
# DÉMARRAGE
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Vérifier les variables d'environnement
    if not os.getenv("PINECONE_API_KEY"):
        print("❌ PINECONE_API_KEY manquante dans .env")
        exit(1)
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY manquante dans .env")
        exit(1)
    
    print("🚀 Démarrage de l'API Adjä...")
    print("📍 URL: http://localhost:8000")
    print("📖 Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload en développement
        log_level="info"
    )