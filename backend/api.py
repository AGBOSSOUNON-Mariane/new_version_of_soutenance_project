"""
API FastAPI - Système RAG Patrimoine Béninois
Production-ready pour React Native
"""

import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


# =============================================================================
# MODÈLES DE DONNÉES (Request/Response)
# =============================================================================

class DebugRequest(BaseModel):
    """Requête pour le mode debug"""
    query: str = Field(..., description="Question de l'utilisateur", min_length=3)
    language: str = Field(default="fr", description="Langue: 'fr' ou 'en'")
    pole_filter: Optional[str] = Field(None, description="Filtrer par pôle")
    top_k: int = Field(default=10, description="Nombre de chunks à récupérer", ge=1, le=50)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Parle-moi du roi Ghézo",
                "language": "fr",
                "pole_filter": None,
                "top_k": 10
            }
        }


class DebugChunk(BaseModel):
    """Chunk avec informations de debug"""
    rank: int
    score: float
    hybrid_score: float
    text_preview: str
    source_file: str
    pole: str
    category: str
    subcategory: str
    images_count: int
    sources_count: int


class DebugResponse(BaseModel):
    """Réponse détaillée pour le debug"""
    success: bool
    query: str
    
    # Détection et filtrage
    entity_detected: Optional[Dict[str, str]]
    filters_applied: Dict[str, Any]
    
    # Pipeline RAG
    pipeline_steps: Dict[str, int]
    
    # Chunks détaillés
    chunks: List[DebugChunk]
    
    # Contexte préparé
    context_preview: str
    context_length: int
    
    # Images et sources
    images: List[str]
    sources: List[str]
    
    # Métadonnées
    timestamp: str
    execution_time_ms: float
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "Parle-moi du roi Ghézo",
                "entity_detected": {
                    "pole": "Abomey",
                    "category": "Rois du Dahomey",
                    "subcategory": "Guézo"
                },
                "filters_applied": {
                    "subcategory": {"$eq": "Guézo"}
                },
                "pipeline_steps": {
                    "pinecone_results": 4,
                    "after_reranking": 4,
                    "after_deduplication": 2,
                    "context_chunks": 2
                },
                "chunks": [],
                "context_preview": "[Source 1: Abomey - Rois du Dahomey]...",
                "context_length": 1944,
                "images": ["palais_du_roi_Ghezo.jpg"],
                "sources": ["Wikipédia (FR) — Ghézo"],
                "timestamp": "2025-01-15T10:30:00",
                "execution_time_ms": 1234.5,
                "error": None
            }
        }


class ChatRequest(BaseModel):
    """Requête de chat depuis l'application mobile"""
    query: str = Field(..., description="Question de l'utilisateur", min_length=3)
    language: str = Field(default="fr", description="Langue de réponse: 'fr' ou 'en'")
    pole_filter: Optional[str] = Field(None, description="Filtrer par pôle (Abomey, Ouidah, Ganvié, Porto Novo)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Parle-moi du roi Ghézo",
                "language": "fr",
                "pole_filter": None
            }
        }


class ChatResponse(BaseModel):
    """Réponse du système RAG"""
    success: bool
    query: str
    response: Optional[str]
    images: List[str]
    sources: List[str]
    pole: Optional[str]
    category: Optional[str]
    language: str
    timestamp: str
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "Parle-moi du roi Ghézo",
                "response": "Ghézo, également orthographié Guézo...",
                "images": ["palais_du_roi_Ghezo.jpg", "Symbole_de_Ghezo.jpg"],
                "sources": ["Wikipédia (FR) — Ghézo"],
                "pole": "Abomey",
                "category": "Rois du Dahomey",
                "language": "fr",
                "timestamp": "2025-01-15T10:30:00",
                "error": None
            }
        }


class HealthResponse(BaseModel):
    """État de santé de l'API"""
    status: str
    version: str
    services: Dict[str, str]
    timestamp: str


# =============================================================================
# SYSTÈME RAG (Backend)
# =============================================================================

class BeninHeritageRAG:
    """Système RAG complet avec génération Gemini"""
    
    def __init__(self):
        """Initialise le système RAG"""
        print("🚀 Initialisation du système RAG...")
        
        # Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index(os.getenv("INDEX_NAME", "benin-heritage"))
        
        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Mapping des entités
        self.entity_mapping = {
            "ghézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "ghezo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "guézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "béhanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "behanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "glèlè": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Glèlè"},
            "agadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agadja"},
            "amazones": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "mino": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "palais royaux": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "route des esclaves": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": ""},
            "temple des pythons": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Temple des Pythons"},
            "musée honmè": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Honmè"},
            "ganvié": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            "houégbadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Houégbadja"},
            "houegbadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Houégbadja"},

        }
        
        print("✅ Système RAG prêt")
    
    def detect_entity(self, query: str) -> Optional[Dict[str, str]]:
        """Détecte les entités dans la question"""
        query_lower = query.lower()
        best_match = None
        best_length = 0
        
        for entity, metadata in self.entity_mapping.items():
            if entity in query_lower and len(entity) > best_length:
                best_match = metadata
                best_length = len(entity)
        
        return best_match
    
    def build_smart_filter(self, query: str, manual_pole: Optional[str] = None) -> tuple:
        """Construit un filtre intelligent"""
        filters = {}
        detected = self.detect_entity(query)
        
        # Filtre manuel prioritaire
        if manual_pole:
            filters['pole'] = {"$eq": manual_pole}
            detected = {"pole": manual_pole, "category": "", "subcategory": ""}
        elif detected:
            if detected.get('subcategory'):
                filters['subcategory'] = {"$eq": detected['subcategory']}
            elif detected.get('category'):
                filters['category'] = {"$eq": detected['category']}
            elif detected.get('pole'):
                filters['pole'] = {"$eq": detected['pole']}
        
        return filters, detected
    
    def extract_keywords(self, query: str) -> List[str]:
        """Extrait les mots-clés"""
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'à', 'dans', 'par', 'pour', 'avec', 'sur', 'que', 'qui', 'est', 'quelle', 'quel', 'comment', 'pourquoi', 'parle', 'moi', 'histoire'}
        words = re.findall(r'\b\w+\b', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def rerank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Reranking hybride"""
        if not results:
            return results
        
        keywords = self.extract_keywords(query)
        
        for result in results:
            pinecone_score = result['score']
            text_lower = result['text'].lower()
            kw_score = sum(1 for kw in keywords if kw in text_lower) / len(keywords) if keywords else 0
            result['hybrid_score'] = 0.6 * pinecone_score + 0.4 * kw_score
        
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return results
    
    def deduplicate_chunks(self, results: List[Dict]) -> List[Dict]:
        """Max 2 chunks par document"""
        deduplicated = []
        for result in results:
            file_count = sum(1 for r in deduplicated if r['source_file'] == result['source_file'])
            if file_count < 2:
                deduplicated.append(result)
        return deduplicated
    
    def clean_text(self, text: str) -> str:
        """Nettoie le texte"""
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def prepare_context(self, results: List[Dict], query: str) -> Dict:
        """Prépare le contexte pour Gemini"""
        selected = results[:3]
        
        context_parts = []
        for i, chunk in enumerate(selected, 1):
            clean_text = self.clean_text(chunk['text'])
            context_parts.append(f"[Source {i}: {chunk['pole']} - {chunk['category']}]")
            context_parts.append(clean_text)
            context_parts.append("")
        
        all_images = []
        all_sources = []
        seen_sources = set()
        
        for chunk in selected:
            all_images.extend(chunk['images'])
            for source in chunk['sources']:
                source_normalized = source.lower().strip()
                if source_normalized not in seen_sources:
                    all_sources.append(source)
                    seen_sources.add(source_normalized)
        
        return {
            'context': '\n'.join(context_parts),
            'images': list(dict.fromkeys(all_images))[:10],
            'sources': all_sources[:5],
            'pole': selected[0]['pole'] if selected else None,
            'category': selected[0]['category'] if selected else None
        }
    
    def build_prompt(self, query: str, context: str, language: str) -> str:
        """Construit le prompt pour Gemini"""
        if language == "fr":
            return f"""Tu es un guide culturel expert du patrimoine béninois. Ta mission est de raconter l'histoire et la culture du Bénin de manière narrative, vivante et accessible.

CONTEXTE DOCUMENTAIRE :
{context}

QUESTION DE L'UTILISATEUR :
{query}

INSTRUCTIONS :
1. Réponds de manière narrative et captivante, comme un conteur
2. Utilise UNIQUEMENT les informations du contexte fourni
3. Structure ta réponse avec des paragraphes clairs
4. Adapte ton ton pour être accessible aux adolescents comme aux adultes
5. Si le contexte ne contient pas assez d'informations, dis-le clairement
6. Ne mentionne JAMAIS les numéros de sources dans ta réponse
7. Reste fidèle aux faits historiques du contexte

RÉPONSE (en français, narrative et structurée) :"""
        else:
            return f"""You are a cultural guide expert on Benin's heritage. Tell the history and culture of Benin in a narrative, lively and accessible way.

DOCUMENTARY CONTEXT:
{context}

USER'S QUESTION:
{query}

INSTRUCTIONS:
1. Respond in a narrative and captivating manner, like a storyteller
2. Use ONLY information from the provided context
3. Structure your response clearly with paragraphs
4. Adapt your tone to be accessible to teenagers and adults
5. If the context doesn't contain enough information, say so clearly
6. NEVER mention source numbers in your response
7. Stay faithful to the historical facts in the context

RESPONSE (in English, narrative and structured):"""
    
    def generate_debug(self, query: str, language: str = "fr", pole_filter: Optional[str] = None, top_k: int = 10) -> Dict[str, Any]:
        """Pipeline complet avec informations de debug détaillées"""
        
        import time
        start_time = time.time()
        
        debug_info = {
            'query': query,
            'entity_detected': None,
            'filters_applied': {},
            'pipeline_steps': {},
            'chunks': [],
            'context_preview': '',
            'context_length': 0,
            'images': [],
            'sources': []
        }
        
        try:
            # 1. Détection d'entité et filtrage
            filter_dict, detected = self.build_smart_filter(query, pole_filter)
            debug_info['entity_detected'] = detected
            debug_info['filters_applied'] = filter_dict
            
            # 2. Recherche Pinecone
            query_embedding = self.embeddings.embed_query(query)
            
            search_params = {
                'vector': query_embedding,
                'top_k': top_k,
                'include_metadata': True
            }
            
            if filter_dict:
                search_params['filter'] = filter_dict
            
            pinecone_results = self.index.query(**search_params)
            
            # 3. Parser résultats
            results = []
            for match in pinecone_results['matches']:
                metadata = match['metadata']
                images = [img.strip() for img in metadata.get('images', '').split('|') if img.strip()]
                
                sources_raw = metadata.get('sources', '')
                sources = []
                for src in sources_raw.replace('\n', '|').split('|'):
                    src = src.strip().lstrip('•').strip()
                    if src:
                        sources.append(src)
                
                results.append({
                    'score': round(match['score'], 4),
                    'text': metadata.get('text', ''),
                    'source_file': metadata.get('source_file', ''),
                    'pole': metadata.get('pole', ''),
                    'category': metadata.get('category', ''),
                    'subcategory': metadata.get('subcategory', ''),
                    'images': images,
                    'sources': sources
                })
            
            debug_info['pipeline_steps']['pinecone_results'] = len(results)
            
            if not results:
                debug_info['success'] = False
                debug_info['error'] = 'Aucun résultat trouvé'
                debug_info['execution_time_ms'] = (time.time() - start_time) * 1000
                return debug_info
            
            # 4. Reranking
            results = self.rerank_results(results, query)
            debug_info['pipeline_steps']['after_reranking'] = len(results)
            
            # 5. Déduplication
            results = self.deduplicate_chunks(results)
            debug_info['pipeline_steps']['after_deduplication'] = len(results)
            
            # 6. Préparer contexte
            context_data = self.prepare_context(results, query)
            debug_info['pipeline_steps']['context_chunks'] = len(results[:3])
            
            debug_info['context_preview'] = context_data['context'][:500] + "..."
            debug_info['context_length'] = len(context_data['context'])
            debug_info['images'] = context_data['images']
            debug_info['sources'] = context_data['sources']
            
            # 7. Construire la liste détaillée des chunks
            for i, result in enumerate(results[:10], 1):
                debug_info['chunks'].append({
                    'rank': i,
                    'score': result['score'],
                    'hybrid_score': result.get('hybrid_score', result['score']),
                    'text_preview': result['text'][:200] + "...",
                    'source_file': result['source_file'],
                    'pole': result['pole'],
                    'category': result['category'],
                    'subcategory': result['subcategory'],
                    'images_count': len(result['images']),
                    'sources_count': len(result['sources'])
                })
            
            debug_info['success'] = True
            debug_info['execution_time_ms'] = (time.time() - start_time) * 1000
            
            return debug_info
            
        except Exception as e:
            debug_info['success'] = False
            debug_info['error'] = str(e)
            debug_info['execution_time_ms'] = (time.time() - start_time) * 1000
            return debug_info


    def generate(self, query: str, language: str = "fr", pole_filter: Optional[str] = None) -> Dict[str, Any]:
        """Pipeline complet de génération"""
        
        # 1. Filtrage
        filter_dict, detected = self.build_smart_filter(query, pole_filter)
        
        # 2. Recherche Pinecone
        query_embedding = self.embeddings.embed_query(query)
        
        search_params = {
            'vector': query_embedding,
            'top_k': 10,
            'include_metadata': True
        }
        
        if filter_dict:
            search_params['filter'] = filter_dict
        
        pinecone_results = self.index.query(**search_params)
        
        # 3. Parser résultats
        results = []
        for match in pinecone_results['matches']:
            metadata = match['metadata']
            images = [img.strip() for img in metadata.get('images', '').split('|') if img.strip()]
            
            sources_raw = metadata.get('sources', '')
            sources = []
            for src in sources_raw.replace('\n', '|').split('|'):
                src = src.strip().lstrip('•').strip()
                if src:
                    sources.append(src)
            
            results.append({
                'score': round(match['score'], 4),
                'text': metadata.get('text', ''),
                'source_file': metadata.get('source_file', ''),
                'pole': metadata.get('pole', ''),
                'category': metadata.get('category', ''),
                'images': images,
                'sources': sources
            })
        
        if not results:
            return {
                'success': False,
                'error': 'Aucun résultat trouvé dans la base de données',
                'response': None,
                'images': [],
                'sources': [],
                'pole': None,
                'category': None
            }
        
        # 4. Reranking et déduplication
        results = self.rerank_results(results, query)
        results = self.deduplicate_chunks(results)
        
        # 5. Préparer contexte
        context_data = self.prepare_context(results, query)
        
        # 6. Générer avec Gemini
        try:
            prompt = self.build_prompt(query, context_data['context'], language)
            
            generation_config = genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
            )
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return {
                'success': True,
                'response': response.text,
                'images': context_data['images'],
                'sources': context_data['sources'],
                'pole': context_data['pole'],
                'category': context_data['category']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur lors de la génération: {str(e)}',
                'response': None,
                'images': context_data['images'],
                'sources': context_data['sources'],
                'pole': context_data['pole'],
                'category': context_data['category']
            }


# =============================================================================
# APPLICATION FASTAPI
# =============================================================================

# Initialiser FastAPI
app = FastAPI(
    title="API Patrimoine Béninois",
    description="API RAG pour l'exploration du patrimoine culturel du Bénin",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS pour React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production: spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser le système RAG (au démarrage)
rag_system: Optional[BeninHeritageRAG] = None


@app.on_event("startup")
async def startup_event():
    """Initialise le système RAG au démarrage de l'API"""
    global rag_system
    print("🚀 Démarrage de l'API...")
    
    # Vérifier les variables d'environnement
    required_vars = ["PINECONE_API_KEY", "GEMINI_API_KEY", "INDEX_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Variables manquantes: {', '.join(missing_vars)}")
        raise RuntimeError(f"Variables d'environnement manquantes: {missing_vars}")
    
    try:
        rag_system = BeninHeritageRAG()
        print("✅ API prête à recevoir des requêtes")
    except Exception as e:
        print(f"❌ Erreur d'initialisation: {e}")
        raise


@app.get("/", response_model=Dict[str, str])
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "API Patrimoine Béninois",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de santé de l'API"""
    return HealthResponse(
        status="healthy" if rag_system else "unhealthy",
        version="1.0.0",
        services={
            "rag": "operational" if rag_system else "down",
            "pinecone": "operational",
            "gemini": "operational"
        },
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal de chat avec le système RAG
    
    - **query**: Question de l'utilisateur (minimum 3 caractères)
    - **language**: Langue de réponse ('fr' ou 'en')
    - **pole_filter**: Filtre optionnel par pôle
    """
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="Service RAG non disponible")
    
    # Valider la langue
    if request.language not in ["fr", "en"]:
        raise HTTPException(status_code=400, detail="Langue invalide. Utilisez 'fr' ou 'en'")
    
    # Générer la réponse
    try:
        result = rag_system.generate(
            query=request.query,
            language=request.language,
            pole_filter=request.pole_filter
        )
        
        return ChatResponse(
            success=result['success'],
            query=request.query,
            response=result.get('response'),
            images=result.get('images', []),
            sources=result.get('sources', []),
            pole=result.get('pole'),
            category=result.get('category'),
            language=request.language,
            timestamp=datetime.now().isoformat(),
            error=result.get('error')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


@app.get("/api/poles")
async def get_poles():
    """Liste des pôles culturels disponibles"""
    return {
        "poles": ["Abomey", "Ouidah", "Ganvié", "Porto Novo"],
        "count": 4
    }


@app.post("/api/rag/debug", response_model=DebugResponse)
async def debug_rag(request: DebugRequest):
    """
    🔍 Endpoint de debug pour analyser le pipeline RAG
    
    Affiche en détail :
    - Entités détectées et filtres appliqués
    - Nombre de chunks à chaque étape du pipeline
    - Scores Pinecone et hybrides
    - Aperçu du contexte préparé pour Gemini
    - Liste complète des chunks avec métadonnées
    
    Très utile pour :
    - Tester le système
    - Comprendre le fonctionnement
    - Démonstrations
    - Debugging
    """
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="Service RAG non disponible")
    
    # Valider la langue
    if request.language not in ["fr", "en"]:
        raise HTTPException(status_code=400, detail="Langue invalide. Utilisez 'fr' ou 'en'")
    
    # Exécuter le pipeline en mode debug
    try:
        debug_result = rag_system.generate_debug(
            query=request.query,
            language=request.language,
            pole_filter=request.pole_filter,
            top_k=request.top_k
        )
        
        return DebugResponse(
            success=debug_result['success'],
            query=debug_result['query'],
            entity_detected=debug_result.get('entity_detected'),
            filters_applied=debug_result.get('filters_applied', {}),
            pipeline_steps=debug_result.get('pipeline_steps', {}),
            chunks=[
                DebugChunk(
                    rank=chunk['rank'],
                    score=chunk['score'],
                    hybrid_score=chunk['hybrid_score'],
                    text_preview=chunk['text_preview'],
                    source_file=chunk['source_file'],
                    pole=chunk['pole'],
                    category=chunk['category'],
                    subcategory=chunk['subcategory'],
                    images_count=chunk['images_count'],
                    sources_count=chunk['sources_count']
                )
                for chunk in debug_result.get('chunks', [])
            ],
            context_preview=debug_result.get('context_preview', ''),
            context_length=debug_result.get('context_length', 0),
            images=debug_result.get('images', []),
            sources=debug_result.get('sources', []),
            timestamp=datetime.now().isoformat(),
            execution_time_ms=debug_result.get('execution_time_ms', 0),
            error=debug_result.get('error')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


# =============================================================================
# LANCEMENT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Lancement de l'API FastAPI...")
    print("📖 Documentation : http://localhost:8000/docs")
    print("🏥 Health check : http://localhost:8000/health")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )