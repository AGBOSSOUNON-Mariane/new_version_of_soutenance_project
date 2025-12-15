"""
Système RAG Complet avec Génération Gemini
Patrimoine Béninois - Version Production
"""

import os
import re
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()


class BeninHeritageRAGWithGemini:
    """
    Système RAG complet avec génération de réponses narratives via Gemini
    """
    
    def __init__(
        self,
        pinecone_api_key: str,
        gemini_api_key: str,
        index_name: str = "benin-heritage"
    ):
        """Initialise le système RAG complet"""
        
        # Pinecone
        print("🔌 Connexion à Pinecone...")
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index(index_name)
        
        # Embeddings
        print("📦 Chargement du modèle d'embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Gemini
        print("🤖 Configuration de Gemini...")
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Mapping des entités
        self.entity_mapping = {
            # Rois
            "ghézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "ghezo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "guézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "béhanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "behanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "glèlè": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Glèlè"},
            "agadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agadja"},
            "houégbadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Houégbadja"},
            "akaba": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Akaba"},
            "toffa": {"pole": "Porto Novo", "category": "Rois de Porto-Novo", "subcategory": ""},
            
            # Amazones
            "amazones": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "mino": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "agodjié": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            
            # Lieux
            "palais royaux": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "route des esclaves": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": ""},
            "temple des pythons": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Temple des Pythons"},
            "musée honmè": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Honmè"},
            "ganvié": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
        }
        
        print("✅ Système RAG complet prêt\n")
    
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
    
    def build_smart_filter(self, query: str) -> tuple:
        """Construit un filtre intelligent"""
        filters = {}
        detected = self.detect_entity(query)
        
        if detected:
            if detected.get('subcategory'):
                filters['subcategory'] = {"$eq": detected['subcategory']}
            elif detected.get('category'):
                filters['category'] = {"$eq": detected['category']}
            elif detected.get('pole'):
                filters['pole'] = {"$eq": detected['pole']}
        
        # Fallback
        if not filters:
            query_lower = query.lower()
            if 'abomey' in query_lower:
                filters['pole'] = {"$eq": "Abomey"}
                detected = {"pole": "Abomey", "category": "", "subcategory": ""}
            elif 'ouidah' in query_lower:
                filters['pole'] = {"$eq": "Ouidah"}
                detected = {"pole": "Ouidah", "category": "", "subcategory": ""}
            elif 'ganvié' in query_lower or 'ganvie' in query_lower:
                filters['pole'] = {"$eq": "Ganvié"}
                detected = {"pole": "Ganvié", "category": "", "subcategory": ""}
            elif 'porto' in query_lower:
                filters['pole'] = {"$eq": "Porto Novo"}
                detected = {"pole": "Porto Novo", "category": "", "subcategory": ""}
        
        return filters, detected
    
    def extract_keywords(self, query: str) -> List[str]:
        """Extrait les mots-clés"""
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
            'à', 'dans', 'par', 'pour', 'avec', 'sur', 'que', 'qui', 'est',
            'quelle', 'quel', 'comment', 'pourquoi', 'parle', 'moi', 'histoire'
        }
        words = re.findall(r'\b\w+\b', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def keyword_score(self, text: str, keywords: List[str]) -> float:
        """Score de présence des keywords"""
        if not keywords:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches / len(keywords)
    
    def rerank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Reranking hybride"""
        if not results:
            return results
        
        keywords = self.extract_keywords(query)
        
        for result in results:
            pinecone_score = result['score']
            kw_score = self.keyword_score(result['text'], keywords)
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
    
    def clean_text_for_llm(self, text: str) -> str:
        """Nettoie le texte"""
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def prepare_llm_context(self, results: List[Dict], query: str) -> Dict:
        """Prépare le contexte pour Gemini"""
        selected = results[:3]
        
        context_parts = []
        for i, chunk in enumerate(selected, 1):
            clean_text = self.clean_text_for_llm(chunk['text'])
            context_parts.append(f"[Source {i}: {chunk['pole']} - {chunk['category']}]")
            context_parts.append(clean_text)
            context_parts.append("")
        
        # Métadonnées dédupliquées
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
        
        unique_images = list(dict.fromkeys(all_images))[:10]
        unique_sources = all_sources[:5]
        
        return {
            'query': query,
            'context': '\n'.join(context_parts),
            'images': unique_images,
            'sources': unique_sources,
            'chunks_used': len(selected)
        }
    
    def build_gemini_prompt(self, query: str, context: str, language: str = "fr") -> str:
        """
        Construit le prompt optimisé pour Gemini
        
        Args:
            query: Question de l'utilisateur
            context: Contexte extrait de la base
            language: 'fr' ou 'en'
        """
        
        if language == "fr":
            prompt = f"""Tu es un guide culturel expert du patrimoine béninois. Ta mission est de raconter l'histoire et la culture du Bénin de manière narrative, vivante et accessible.

CONTEXTE DOCUMENTAIRE :
{context}

QUESTION DE L'UTILISATEUR :
{query}

INSTRUCTIONS :
1. Réponds de manière narrative et captivante, comme un conteur
2. Utilise UNIQUEMENT les informations du contexte fourni
3. Structure ta réponse de manière claire avec des paragraphes
4. Adapte ton ton pour être accessible aux adolescents comme aux adultes
5. Si le contexte ne contient pas assez d'informations, dis-le clairement
6. Ne mentionne JAMAIS les numéros de sources ([Source 1], [Source 2]) dans ta réponse
7. Reste fidèle aux faits historiques du contexte

RÉPONSE (en français, narrative et structurée) :"""
        
        else:  # English
            prompt = f"""You are a cultural guide expert on Benin's heritage. Your mission is to tell the history and culture of Benin in a narrative, lively and accessible way.

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
6. NEVER mention source numbers ([Source 1], [Source 2]) in your response
7. Stay faithful to the historical facts in the context

RESPONSE (in English, narrative and structured):"""
        
        return prompt
    
    def generate_response(
        self,
        query: str,
        language: str = "fr",
        top_k: int = 10,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Pipeline complet : Retrieval + Génération
        
        Args:
            query: Question de l'utilisateur
            language: 'fr' ou 'en'
            top_k: Nombre de chunks à récupérer
            verbose: Afficher les logs
            
        Returns:
            Dict avec la réponse générée + métadonnées
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"🔍 QUESTION: {query}")
            print(f"{'='*80}")
        
        # 1. Filtres intelligents
        filter_dict, detected = self.build_smart_filter(query)
        
        if verbose and detected:
            print(f"🤖 Entité détectée:")
            if detected.get('subcategory'):
                print(f"   📁 {detected['subcategory']}")
            if detected.get('category'):
                print(f"   📂 {detected['category']}")
            if detected.get('pole'):
                print(f"   📍 {detected['pole']}")
        
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
                'id': match['id'],
                'score': round(match['score'], 4),
                'text': metadata.get('text', ''),
                'source_file': metadata.get('source_file', ''),
                'pole': metadata.get('pole', ''),
                'category': metadata.get('category', ''),
                'subcategory': metadata.get('subcategory', ''),
                'images': images,
                'sources': sources
            })
        
        if verbose:
            print(f"\n📊 Pipeline RAG:")
            print(f"   1️⃣ Pinecone: {len(results)} chunks")
        
        # 4. Reranking
        if results:
            results = self.rerank_results(results, query)
            if verbose:
                print(f"   2️⃣ Reranking: {len(results)} chunks")
        
        # 5. Déduplication
        if results:
            results = self.deduplicate_chunks(results)
            if verbose:
                print(f"   3️⃣ Déduplication: {len(results)} chunks")
        
        # 6. Préparer contexte
        if not results:
            return {
                'success': False,
                'error': 'Aucun résultat trouvé dans la base de données',
                'query': query,
                'response': None,
                'images': [],
                'sources': []
            }
        
        llm_context = self.prepare_llm_context(results, query)
        
        if verbose:
            print(f"   4️⃣ Contexte LLM: {llm_context['chunks_used']} chunks, {len(llm_context['context'])} caractères")
        
        # 7. Générer avec Gemini
        if verbose:
            print(f"\n🤖 Génération avec Gemini...")
        
        try:
            prompt = self.build_gemini_prompt(query, llm_context['context'], language)
            
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
            
            generated_text = response.text
            
            if verbose:
                print(f"✅ Réponse générée ({len(generated_text)} caractères)")
            
            return {
                'success': True,
                'query': query,
                'response': generated_text,
                'images': llm_context['images'],
                'sources': llm_context['sources'],
                'chunks_used': llm_context['chunks_used'],
                'retrieval_scores': {
                    'top_score': max([r['score'] for r in results]),
                    'avg_score': sum([r['score'] for r in results]) / len(results)
                },
                'language': language
            }
            
        except Exception as e:
            if verbose:
                print(f"❌ Erreur Gemini: {e}")
            
            return {
                'success': False,
                'error': f'Erreur lors de la génération: {str(e)}',
                'query': query,
                'response': None,
                'images': llm_context['images'],
                'sources': llm_context['sources']
            }


# =============================================================================
# AFFICHAGE FORMATÉ
# =============================================================================

def display_response(result: Dict[str, Any]):
    """Affiche la réponse de manière élégante"""
    
    print(f"\n{'='*80}")
    print(f"📖 RÉPONSE GÉNÉRÉE")
    print(f"{'='*80}\n")
    
    if not result['success']:
        print(f"❌ {result['error']}")
        return
    
    # Réponse narrative
    print(result['response'])
    
    # Images
    if result['images']:
        print(f"\n{'─'*80}")
        print(f"🖼️  IMAGES DISPONIBLES ({len(result['images'])})")
        print(f"{'─'*80}")
        for i, img in enumerate(result['images'], 1):
            print(f"{i}. {os.path.basename(img)}")
    
    # Sources
    if result['sources']:
        print(f"\n{'─'*80}")
        print(f"📚 SOURCES BIBLIOGRAPHIQUES")
        print(f"{'─'*80}")
        for i, src in enumerate(result['sources'], 1):
            print(f"{i}. {src}")
    
    # Métadonnées
    print(f"\n{'─'*80}")
    print(f"📊 MÉTADONNÉES")
    print(f"{'─'*80}")
    print(f"Chunks utilisés: {result['chunks_used']}")
    if 'retrieval_scores' in result:
        print(f"Score retrieval: {result['retrieval_scores']['avg_score']*100:.1f}%")
    print(f"Langue: {result['language'].upper()}")


# =============================================================================
# TESTS
# =============================================================================

def run_generation_tests():
    """Teste le système complet avec génération"""
    
    print("🚀 TEST DU SYSTÈME RAG AVEC GÉNÉRATION GEMINI")
    print("="*80)
    
    # Initialiser
    rag = BeninHeritageRAGWithGemini(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )
    
    # Questions de test
    test_queries = [
        ("Parle-moi du roi Ghézo", "fr"),
        ("Histoire des Amazones du Dahomey", "fr"),
        ("What is the Temple of Pythons in Ouidah?", "en"),
        ("Parle-moi du Musée Honmè à Porto-Novo", "fr"),
    ]
    
    for query, lang in test_queries:
        result = rag.generate_response(query, language=lang, verbose=True)
        display_response(result)
        
        print(f"\n{'='*80}\n")
        input("⏸️  Appuyez sur Entrée pour continuer...\n")
    
    print("✅ TOUS LES TESTS TERMINÉS !")


if __name__ == "__main__":
    # Vérifier configuration
    if not os.getenv("PINECONE_API_KEY"):
        print("❌ PINECONE_API_KEY manquante dans .env")
        exit(1)
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY manquante dans .env")
        print("\nPour obtenir une clé Gemini:")
        print("1. Allez sur https://makersuite.google.com/app/apikey")
        print("2. Créez une clé API")
        print("3. Ajoutez GEMINI_API_KEY=votre_cle dans .env")
        exit(1)
    
    run_generation_tests()