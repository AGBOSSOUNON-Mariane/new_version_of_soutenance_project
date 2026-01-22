"""
API FastAPI pour Agent Conversationnel Adjä
Patrimoine Béninois - Version Production avec TTS
Endpoints : Chat, Chat+Audio, Historique, Reset, Health Check
VERSION PRODUCTION - URL Dynamique
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

# Import de ton agent
from rag_conversational_agent_correction import BeninHeritageConversationalAgent

# 🆕 Import du service TTS
from tts_service import TTSService, AudioResponse

load_dotenv()

# ✅ URL DE BASE (local ou production) - CORRECTION CRITIQUE
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

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
    version="2.1.0",  # 🆕 Version avec TTS
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
IMAGES_DIR = Path("Donnees_soutenance")  # ← Ton dossier de données
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
    """Requête de chat avec support TTS"""
    message: str = Field(..., min_length=1, max_length=500, description="Message de l'utilisateur")
    session_id: Optional[str] = Field(None, description="ID de session (auto-généré si absent)")
    language: Optional[str] = Field(
        None, 
        pattern="^(fr|en)$", 
        description="Langue souhaitée (optionnel, auto-détectée si null)"
    )
    generate_audio: bool = Field(True, description="🆕 Générer l'audio de la réponse")
    verbose: bool = Field(False, description="Activer les logs détaillés")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qui est le roi Ghézo ?",
                "session_id": "user-123-abc",
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
    
    # 🆕 Champs audio
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

# 🆕 Nouveau modèle pour endpoint audio dédié
class AudioGenerateRequest(BaseModel):
    """Requête de génération audio uniquement"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field("fr", pattern="^(fr|en)$")
    force_regenerate: bool = Field(False)

# =============================================================================
# ENDPOINTS PRINCIPAUX
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur l'API Adjä - Guide Culturel Béninois avec TTS",
        "version": "2.1.0",
        "status": "operational",
        "features": {
            "chat": "Conversation intelligente",
            "rag": "Recherche documentaire",
            "tts": "🆕 Génération audio automatique",
            "multilingual": "Français & Anglais"
        },
        "endpoints": {
            "chat": "/chat",
            "audio": "/audio/{filename}",
            "generate_audio": "/generate-audio",
            "history": "/history/{session_id}",
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
        
        # 🆕 Vérifier TTS
        tts_ok = tts_service is not None
        audio_dir_ok = AUDIO_DIR.exists()
        
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
            "audio_files_count": len(list(AUDIO_DIR.glob("*.mp3")))
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
    """Endpoint principal avec TTS"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Détection langue
        if request.language is None:
            detected_language = detect_language(request.message)
        else:
            detected_language = request.language
        
        # 🆕 LOG REQUÊTE
        print(f"\n{'='*80}")
        print(f"📥 NOUVELLE REQUÊTE")
        print(f"{'='*80}")
        print(f"Session: {session_id}")
        print(f"Message: {request.message}")
        print(f"Langue: {detected_language}")
        print(f"Générer audio: {request.generate_audio}")
        print(f"Verbose: {request.verbose}")
        
        # Agent RAG
        agent = get_or_create_agent(session_id)
        result = agent.generate_response(
            query=request.message,
            language=detected_language,
            verbose=True  # ← FORCE VERBOSE ICI
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # 🆕 LOG RÉSULTAT RAG
        print(f"\n{'─'*80}")
        print(f"✅ RÉSULTAT RAG")
        print(f"{'─'*80}")
        print(f"Intent: {result.get('intent')}")
        print(f"RAG utilisé: {result.get('used_rag')}")
        print(f"Chunks: {result.get('chunks_used', 0)}")
        print(f"Images: {len(result.get('images', []))}")
        print(f"Sources: {len(result.get('sources', []))}")
        print(f"Réponse (longueur): {len(result['response'])} caractères")
        print(f"Réponse (100 premiers): {result['response'][:100]}...")
        
        if result.get('images'):
            print(f"\n📸 Images retournées:")
            for i, img in enumerate(result['images'][:5], 1):
                print(f"   {i}. {img}")
        
        if result.get('sources'):
            print(f"\n📚 Sources retournées:")
            for i, src in enumerate(result['sources'][:5], 1):
                print(f"   {i}. {src}")
        
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
            
            # ✅ APRÈS (CORRIGÉ) - audio_result est un DICT, pas un objet
            # Le service TTS retourne un dict Python
            if isinstance(audio_result, dict) and audio_result.get('success'):
                audio_available = True
                audio_filename = audio_result.get('audio_filename')
                audio_duration = audio_result.get('duration_seconds')
                
                if audio_filename:
                    # ✅ CORRECTION CRITIQUE : URL DYNAMIQUE
                    audio_url = f"{BASE_URL}/audio/{audio_filename}"
                    print(f"✅ Audio: {audio_filename} ({audio_duration}s)")
                    print(f"✅ URL: {audio_url}")
            else:
                error_msg = audio_result.get('error', 'Erreur inconnue') if isinstance(audio_result, dict) else 'Erreur audio'
                print(f"⚠️ Audio non généré: {error_msg}")
        
        # 🆕 LOG RÉPONSE FINALE
        print(f"\n{'='*80}")
        print(f"📤 RÉPONSE ENVOYÉE AU CLIENT")
        print(f"{'='*80}")
        print(f"Texte: {len(result['response'])} caractères")
        print(f"Images: {len(result.get('images', []))}")
        print(f"Sources: {len(result.get('sources', []))}")
        print(f"Audio: {audio_available}")
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

# 🆕 ENDPOINT AUDIO DÉDIÉ
@app.post("/generate-audio", tags=["Audio"])
async def generate_audio(request: AudioGenerateRequest):
    """
    🆕 Génère un fichier audio à partir d'un texte (sans conversation)
    
    Utile pour générer l'audio d'un texte arbitraire, 
    sans passer par le chat.
    
    Args:
        - **text**: Texte à convertir en audio
        - **language**: Langue ('fr' ou 'en')
        - **force_regenerate**: Forcer la régénération
    
    Returns:
        URL du fichier audio généré
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
        
        # ✅ CORRECTION CRITIQUE : URL DYNAMIQUE
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

# 🆕 ENDPOINT STREAMING AUDIO (optionnel)
@app.post("/generate-audio/stream", tags=["Audio"])
async def generate_audio_stream(request: AudioGenerateRequest):
    """
    🆕 Génère et stream l'audio en temps réel (sans sauvegarder sur disque)
    
    Utile pour les applications qui veulent l'audio directement 
    sans passer par un fichier.
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

@app.get("/history/{session_id}", response_model=HistoryResponse, tags=["Chat"])
async def get_history(session_id: str):
    """Récupère l'historique de conversation"""
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

# 🆕 MAINTENANCE AUDIO
@app.post("/audio/cleanup", tags=["Audio", "Maintenance"])
async def cleanup_audio_files(max_files: int = 100):
    """
    🆕 Nettoie les vieux fichiers audio
    
    Garde seulement les N fichiers les plus récents
    pour éviter de saturer le disque.
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
    
    # ✅ Port dynamique pour Render
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Démarrage du serveur sur le port {port}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=120  # Timeout plus long pour les requêtes lentes
    )