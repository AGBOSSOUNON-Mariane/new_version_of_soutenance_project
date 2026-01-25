"""
API FastAPI pour Agent Conversationnel 
Patrimoine Béninois - Version Production avec TTS + Historique
Endpoints : Chat, Chat+Audio, Historique, Reset, Health Check
VERSION PRODUCTION - URL Dynamique + Historique Utilisateur
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langdetect import detect, LangDetectException
import json
import time
from fastapi.responses import StreamingResponse
import asyncio

# Import de ton agent
from rag_conversational_agent_correction import BeninHeritageConversationalAgent

# 🆕 Import du service TTS
from tts_service import TTSService, AudioResponse

load_dotenv()

# ✅ URL DE BASE (local ou production) - CORRECTION CRITIQUE
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# 🔥 NOUVEAU : Base de données temporaire pour l'historique
conversation_history_db = {}  # {user_id: [conversations]}

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
    """
    try:
        text_clean = text.strip()
        
        if len(text_clean) < 3:
            return default
        
        detected = detect(text_clean)
        
        if detected in ['fr', 'en']:
            return detected
        else:
            print(f"⚠️ Langue détectée '{detected}' non supportée, utilisation de '{default}'")
            return default
            
    except LangDetectException as e:
        print(f"⚠️ Impossible de détecter la langue: {e}, utilisation de '{default}'")
        return default
    except Exception as e:
        print(f"❌ Erreur détection langue: {e}, utilisation de '{default}'")
        return default

# =============================================================================
# CONFIGURATION
# =============================================================================

app = FastAPI(
    title="API - Assistant Patrimoine Béninois",
    description="API conversationnelle avec TTS pour la découverte du patrimoine béninois",
    version="2.2.0",  # 🔥 Version avec TTS + Historique
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🆕 Servir les fichiers audio statiques
AUDIO_DIR = Path("audio_outputs")
AUDIO_DIR.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")


# 🆕 SERVIR LES IMAGES
IMAGES_DIR = Path("Donnees_soutenance")
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
    print(f"✅ Images servies depuis: {IMAGES_DIR}")
else:
    print(f"⚠️ Dossier images introuvable: {IMAGES_DIR}")

# =============================================================================
# SERVICES
# =============================================================================

# Stockage en mémoire des agents par session
sessions: Dict[str, BeninHeritageConversationalAgent] = {}

# 🆕 Service TTS global
tts_service = TTSService()

def get_or_create_agent(session_id: str) -> BeninHeritageConversationalAgent:
    """Récupère ou crée un agent pour une session"""
    if session_id not in sessions:
        sessions[session_id] = BeninHeritageConversationalAgent(
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            index_name=os.getenv("INDEX_NAME", "benin-heritage"),
            max_history=5
        )
    return sessions[session_id]

# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class ChatRequest(BaseModel):
    """Requête de chat avec support TTS + Historique"""
    message: str = Field(..., min_length=1, max_length=500, description="Message de l'utilisateur")
    session_id: Optional[str] = Field(None, description="ID de session (auto-généré si absent)")
    user_id: Optional[str] = Field("anonymous", description="🔥 ID utilisateur pour historique")
    user_profile: Optional[str] = Field("touriste", description="🔥 Profil utilisateur (touriste/étudiant/élève)")
    language: Optional[str] = Field(
        None, 
        pattern="^(fr|en)$", 
        description="Langue souhaitée (optionnel, auto-détectée si null)"
    )
    generate_audio: bool = Field(True, description="Générer l'audio de la réponse")
    verbose: bool = Field(False, description="Activer les logs détaillés")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qui est le roi Ghézo ?",
                "session_id": "user-123-abc",
                "user_id": "anonymous",
                "user_profile": "touriste",
                "language": None,
                "generate_audio": True,
                "verbose": False
            }
        }

class ChatResponse(BaseModel):
    """Réponse de chat avec audio optionnel"""
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
    
    # Champs audio
    audio_available: bool = False
    audio_url: Optional[str] = None
    audio_filename: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "user-123-abc",
                "query": "Qui est le roi Ghézo ?",
                "response": "Ah, le roi Ghézo ! Quelle excellente question...",
                "images": ["palais_ghezo.jpg"],
                "sources": ["Wikipédia FR - Ghézo"],
                "used_rag": True,
                "intent": "heritage_question",
                "language": "fr",
                "chunks_used": 2,
                "timestamp": "2025-01-15T10:30:00",
                "audio_available": True,
                "audio_url": "http://localhost:8000/audio/abc123_fr.mp3",
                "audio_filename": "abc123_fr.mp3",
                "audio_duration_seconds": 15.3
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

class AudioGenerateRequest(BaseModel):
    """Requête de génération audio uniquement"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field("fr", pattern="^(fr|en)$")
    force_regenerate: bool = Field(False)

# 🔥 NOUVEAUX MODÈLES POUR HISTORIQUE
class HistoryItem(BaseModel):
    """Item d'historique"""
    id: str
    user_id: str
    session_id: str
    query: str
    response: str
    user_profile: str
    language: str
    confidence: float
    processing_time: float
    response_type: str
    images_count: int
    sources_count: int
    metadata: str
    timestamp: str

class UserHistoryResponse(BaseModel):
    """Historique utilisateur"""
    user_id: str
    conversations: List[Dict[str, Any]]
    count: int
    total: int
    limit: int
    offset: int
    includes_tts: bool

# =============================================================================
# ENDPOINTS PRINCIPAUX
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur l'API Adjä - Guide Culturel Béninois avec TTS + Historique",
        "version": "2.2.0",
        "status": "operational",
        "features": {
            "chat": "Conversation intelligente",
            "rag": "Recherche documentaire",
            "tts": "Génération audio automatique",
            "history": "🔥 Historique utilisateur",
            "multilingual": "Français & Anglais"
        },
        "endpoints": {
            "chat": "/chat",
            "audio": "/audio/{filename}",
            "generate_audio": "/generate-audio",
            "history_session": "/history/{session_id}",
            "history_user": "🔥 /history/user/{user_id}",
            "reset": "/reset/{session_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Vérifie la santé de l'API + TTS"""
    try:
        pinecone_ok = bool(os.getenv("PINECONE_API_KEY"))
        gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
        tts_ok = tts_service is not None
        audio_dir_ok = AUDIO_DIR.exists()
        
        # 🔥 Statistiques historique
        total_users = len(conversation_history_db)
        total_conversations = sum(len(convs) for convs in conversation_history_db.values())
        
        return {
            "status": "healthy" if (pinecone_ok and gemini_ok and tts_ok) else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "pinecone": "connected" if pinecone_ok else "missing_key",
                "gemini": "connected" if gemini_ok else "missing_key",
                "tts": "operational" if tts_ok else "unavailable",
                "audio_storage": "ready" if audio_dir_ok else "error"
            },
            "active_sessions": len(sessions),
            "audio_files_count": len(list(AUDIO_DIR.glob("*.mp3"))),
            "history": {
                "total_users": total_users,
                "total_conversations": total_conversations
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint principal avec TTS + Sauvegarde historique"""
    start_time = time.time()
    
    try:
        session_id = request.session_id or str(uuid.uuid4())
        user_id = request.user_id
        
        # Détection langue
        if request.language is None:
            detected_language = detect_language(request.message)
        else:
            detected_language = request.language
        
        print(f"\n{'='*80}")
        print(f"📥 NOUVELLE REQUÊTE")
        print(f"{'='*80}")
        print(f"Session: {session_id}")
        print(f"User ID: {user_id}")
        print(f"Profil: {request.user_profile}")
        print(f"Message: {request.message}")
        print(f"Langue: {detected_language}")
        print(f"Générer audio: {request.generate_audio}")
        
        # Agent RAG
        agent = get_or_create_agent(session_id)
        result = agent.generate_response(
            query=request.message,
            language=detected_language,
            verbose=True
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        processing_time = time.time() - start_time
        
        print(f"\n{'─'*80}")
        print(f"✅ RÉSULTAT RAG")
        print(f"{'─'*80}")
        print(f"Intent: {result.get('intent')}")
        print(f"RAG utilisé: {result.get('used_rag')}")
        print(f"Chunks: {result.get('chunks_used', 0)}")
        print(f"Images: {len(result.get('images', []))}")
        print(f"Sources: {len(result.get('sources', []))}")
        print(f"Temps: {processing_time:.2f}s")
        
        # Génération audio
        audio_url = None
        audio_filename = None
        audio_duration = None
        audio_available = False

        if request.generate_audio:
            print(f"\n🔊 Génération audio...")
            audio_result = tts_service.generate_audio(
                text=result['response'],
                language=detected_language
            )
            
            if isinstance(audio_result, dict) and audio_result.get('success'):
                audio_available = True
                audio_filename = audio_result.get('audio_filename')
                audio_duration = audio_result.get('duration_seconds')
                
                if audio_filename:
                    audio_url = f"{BASE_URL}/audio/{audio_filename}"
                    print(f"✅ Audio: {audio_filename} ({audio_duration}s)")
            else:
                error_msg = audio_result.get('error', 'Erreur inconnue') if isinstance(audio_result, dict) else 'Erreur audio'
                print(f"⚠️ Audio non généré: {error_msg}")
        
        # 🔥 SAUVEGARDE DANS L'HISTORIQUE
        conversation_entry = {
            "id": f"{session_id}_{int(datetime.now().timestamp() * 1000)}",
            "user_id": user_id,
            "session_id": session_id,
            "query": request.message,
            "response": result['response'],
            "user_profile": request.user_profile,
            "language": detected_language,
            "confidence": 0.85,  # Tu peux calculer ça dynamiquement si besoin
            "processing_time": processing_time,
            "response_type": result.get('intent', 'success'),
            "images_count": len(result.get('images', [])),
            "sources_count": len(result.get('sources', [])),
            "metadata": json.dumps({
                "sites_covered": [],
                "intent": result.get('intent', ''),
                "used_rag": result.get('used_rag', False),
                "chunks_used": result.get('chunks_used', 0)
            }),
            "timestamp": datetime.now().isoformat()
        }
        
        # Initialiser la liste si nécessaire
        if user_id not in conversation_history_db:
            conversation_history_db[user_id] = []
        
        # Ajouter l'entrée
        conversation_history_db[user_id].append(conversation_entry)
        
        # Limiter à 500 conversations par utilisateur
        if len(conversation_history_db[user_id]) > 500:
            conversation_history_db[user_id] = conversation_history_db[user_id][-500:]
        
        print(f"💾 Historique sauvegardé pour {user_id} ({len(conversation_history_db[user_id])} conversations)")
        
        print(f"\n{'='*80}")
        print(f"📤 RÉPONSE ENVOYÉE AU CLIENT")
        print(f"{'='*80}\n")
        
        # Réponse
        return ChatResponse(
            success=True,
            session_id=session_id,
            query=result['query'],
            response=result['response'],
            images=result.get('images', []),
            sources=result.get('sources', []),
            used_rag=result.get('used_rag', False),
            intent=result.get('intent', 'unknown'),
            language=detected_language,
            chunks_used=result.get('chunks_used'),
            timestamp=datetime.utcnow().isoformat(),
            audio_available=audio_available,
            audio_url=audio_url,
            audio_filename=audio_filename,
            audio_duration_seconds=audio_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# =============================================================================
# 🔥 ENDPOINTS HISTORIQUE UTILISATEUR (NOUVEAUX)
# =============================================================================

@app.get("/history/user/{user_id}", tags=["History"])
async def get_user_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    include_tts: bool = False
):
    """
    🔥 Récupérer l'historique complet d'un utilisateur
    """
    try:
        user_conversations = conversation_history_db.get(user_id, [])
        
        # Trier par date décroissante
        sorted_conversations = sorted(
            user_conversations, 
            key=lambda x: x['timestamp'], 
            reverse=True
        )
        
        # Pagination
        paginated = sorted_conversations[offset:offset + limit]
        
        print(f"📊 Historique {user_id}: {len(paginated)}/{len(user_conversations)} conversations")
        
        return {
            "user_id": user_id,
            "conversations": paginated,
            "count": len(paginated),
            "total": len(user_conversations),
            "limit": limit,
            "offset": offset,
            "includes_tts": include_tts
        }
        
    except Exception as e:
        print(f"❌ Erreur get_user_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/session/{user_id}/{session_id}", tags=["History"])
async def get_session_history_by_user(user_id: str, session_id: str):
    """
    🔥 Récupérer l'historique d'une session spécifique
    """
    try:
        user_conversations = conversation_history_db.get(user_id, [])
        
        session_conversations = [
            conv for conv in user_conversations 
            if conv['session_id'] == session_id
        ]
        
        session_conversations.sort(key=lambda x: x['timestamp'])
        
        print(f"📊 Session {session_id}: {len(session_conversations)} conversations")
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "conversations": session_conversations,
            "count": len(session_conversations)
        }
        
    except Exception as e:
        print(f"❌ Erreur get_session_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/user/{user_id}", tags=["History"])
async def clear_user_history(user_id: str):
    """
    🔥 Effacer tout l'historique d'un utilisateur
    """
    try:
        if user_id in conversation_history_db:
            count = len(conversation_history_db[user_id])
            del conversation_history_db[user_id]
            print(f"🗑️ Historique effacé pour {user_id}: {count} conversations")
            return {
                "message": f"Historique effacé pour {user_id}",
                "deleted_count": count,
                "success": True
            }
        else:
            print(f"⚠️ Aucun historique trouvé pour {user_id}")
            return {
                "message": "Aucun historique trouvé",
                "deleted_count": 0,
                "success": True
            }
            
    except Exception as e:
        print(f"❌ Erreur clear_user_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/stats/{user_id}", tags=["History"])
async def get_user_stats(user_id: str):
    """
    🔥 Statistiques d'utilisation d'un utilisateur
    """
    try:
        user_conversations = conversation_history_db.get(user_id, [])
        
        if not user_conversations:
            return {
                "user_id": user_id,
                "total_conversations": 0,
                "sites_visited": [],
                "avg_confidence": 0,
                "total_processing_time": 0
            }
        
        sites = set()
        total_confidence = 0
        total_time = 0
        
        for conv in user_conversations:
            try:
                metadata = json.loads(conv['metadata'])
                sites.update(metadata.get('sites_covered', []))
            except:
                pass
            total_confidence += conv['confidence']
            total_time += conv['processing_time']
        
        return {
            "user_id": user_id,
            "total_conversations": len(user_conversations),
            "sites_visited": list(sites),
            "avg_confidence": total_confidence / len(user_conversations) if user_conversations else 0,
            "total_processing_time": total_time,
            "avg_processing_time": total_time / len(user_conversations) if user_conversations else 0
        }
        
    except Exception as e:
        print(f"❌ Erreur get_user_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ENDPOINTS AUDIO
# =============================================================================

@app.post("/generate-audio", tags=["Audio"])
async def generate_audio(request: AudioGenerateRequest):
    """
    Génère un fichier audio à partir d'un texte
    """
    try:
        result = tts_service.generate_audio(
            text=request.text,
            language=request.language,
            force_regenerate=request.force_regenerate
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error
            )
        
        audio_url = f"{BASE_URL}/audio/{result.audio_filename}"
        
        return {
            "success": True,
            "audio_url": audio_url,
            "audio_filename": result.audio_filename,
            "duration_seconds": result.duration_seconds,
            "text_length": result.text_length,
            "language": result.language,
            "cached": result.cached
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur génération audio: {str(e)}"
        )

@app.post("/generate-audio/stream", tags=["Audio"])
async def generate_audio_stream(request: AudioGenerateRequest):
    """
    Génère et stream l'audio en temps réel
    """
    try:
        audio_buffer = tts_service.generate_audio_stream(
            text=request.text,
            language=request.language
        )
        
        if audio_buffer is None:
            raise HTTPException(
                status_code=500,
                detail="Échec de la génération audio"
            )
        
        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=audio_{request.language}.mp3"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur streaming audio: {str(e)}"
        )

# =============================================================================
# ENDPOINTS CHAT (SESSION-BASED - ANCIEN SYSTÈME)
# =============================================================================

@app.get("/history/{session_id}", response_model=HistoryResponse, tags=["Chat"])
async def get_history(session_id: str):
    """Récupère l'historique de conversation (par session)"""
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
    """Réinitialise la conversation"""
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

# =============================================================================
# MAINTENANCE
# =============================================================================

@app.post("/audio/cleanup", tags=["Audio", "Maintenance"])
async def cleanup_audio_files(max_files: int = 100):
    """
    Nettoie les vieux fichiers audio
    """
    try:
        tts_service.cleanup_old_files(max_files=max_files)
        
        remaining_files = len(list(AUDIO_DIR.glob("*.mp3")))
        
        return {
            "success": True,
            "message": f"Nettoyage effectué, {remaining_files} fichiers restants",
            "max_files": max_files,
            "remaining_files": remaining_files
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur nettoyage: {str(e)}"
        )

# =============================================================================
# GESTION D'ERREURS
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
# LANCEMENT DU SERVEUR
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Démarrage du serveur sur le port {port}")
    print(f"📊 Historique activé : Base de données en mémoire")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=120
    )