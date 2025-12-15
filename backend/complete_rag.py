"""
Système RAG Optimisé Complet - Patrimoine Béninois
Exécutable directement avec python complete_rag.py
"""

import os
import re
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class OptimizedBeninRAG:
    """
    Système RAG optimisé avec:
    - Filtrage hiérarchique intelligent
    - Reranking hybride (vectoriel + lexical)
    - Déduplication des chunks
    - Préparation contexte LLM propre
    """
    
    def __init__(self, pinecone_api_key: str, index_name: str = "benin-heritage"):
        """Initialise le système RAG"""
        self.index_name = index_name
        
        print("🔌 Connexion à Pinecone...")
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index(index_name)
        
        print("📦 Chargement du modèle d'embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Mapping des entités (40+ entités)
        self.entity_mapping = {
            # Rois du Dahomey
            "ghézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "ghezo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "guézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "béhanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "behanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "glèlè": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Glèlè"},
            "glele": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Glèlè"},
            "agadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agadja"},
            "houégbadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Houégbadja"},
            "akaba": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Akaba"},
            "agoli-agbo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agoli-Agbo"},
            "kpengla": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Kpengla"},
            "toffa": {"pole": "Porto Novo", "category": "Rois de Porto-Novo", "subcategory": ""},
            
            # Amazones
            "amazones": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "mino": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "agodjié": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            
            # Lieux Abomey
            "palais royaux": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "musée historique abomey": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Musée historique d'Abomey"},
            
            # Ouidah
            "route des esclaves": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": ""},
            "porte du non-retour": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Porte du Non-Retour"},
            "arbre de l'oubli": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Arbre de l'Oubli"},
            "temple des pythons": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Temple des Pythons"},
            "fort portugais": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Fort Portugais – Musée d'Histoire"},
            "basilique": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Basilique de l'Immaculée Conception"},
            
            # Ganvié
            "ganvié": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            "cité lacustre": {"pole": "Ganvié", "category": "Mode de vie des habitants de Ganvié et marché flottant", "subcategory": ""},
            
            # Porto-Novo
            "musée honmè": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Honmè"},
            "musée da silva": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Da Silva"},
            "grande mosquée": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Grande Mosquée afro-brésilienne"},
        }
        
        print("✅ RAG optimisé prêt")
        print(f"   📚 {len(self.entity_mapping)} entités mappées\n")
    
    def detect_entity(self, query: str) -> Optional[Dict[str, str]]:
        """Détecte automatiquement les entités dans la question"""
        query_lower = query.lower()
        best_match = None
        best_length = 0
        
        for entity, metadata in self.entity_mapping.items():
            if entity in query_lower and len(entity) > best_length:
                best_match = metadata
                best_length = len(entity)
        
        return best_match
    
    def build_smart_filter(self, query: str) -> tuple:
        """Construit un filtre intelligent avec auto-détection"""
        filters = {}
        detected = self.detect_entity(query)
        
        # Hiérarchie: subcategory > category > pole
        if detected:
            if detected.get('subcategory'):
                filters['subcategory'] = {"$eq": detected['subcategory']}
            elif detected.get('category'):
                filters['category'] = {"$eq": detected['category']}
            elif detected.get('pole'):
                filters['pole'] = {"$eq": detected['pole']}
        
        # Fallback si aucun filtre
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
        """Extrait les mots-clés pertinents"""
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
            'à', 'dans', 'par', 'pour', 'avec', 'sur', 'que', 'qui', 'est',
            'quelle', 'quel', 'comment', 'pourquoi', 'parle', 'moi', 'histoire'
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords
    
    def keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calcule le score de présence des mots-clés"""
        if not keywords:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches / len(keywords)
    
    def rerank_results(self, results: List[Dict], query: str, alpha: float = 0.6) -> List[Dict]:
        """Reranking hybride: score Pinecone + keywords"""
        if not results:
            return results
        
        keywords = self.extract_keywords(query)
        
        for result in results:
            pinecone_score = result['score']
            kw_score = self.keyword_score(result['text'], keywords)
            result['hybrid_score'] = alpha * pinecone_score + (1 - alpha) * kw_score
            result['keyword_score'] = kw_score
        
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
        """Nettoie le texte pour le LLM"""
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def prepare_llm_context(self, results: List[Dict], query: str, max_chunks: int = 3) -> Dict:
        """Prépare le contexte optimisé pour Gemini"""
        selected = results[:max_chunks]
        
        context_parts = []
        for i, chunk in enumerate(selected, 1):
            clean_text = self.clean_text_for_llm(chunk['text'])
            context_parts.append(f"[Source {i}: {chunk['pole']} - {chunk['category']}]")
            context_parts.append(clean_text)
            context_parts.append("")
        
        # Collecter métadonnées
        all_images = []
        all_sources = []
        seen_sources = set()  # Pour détecter les doublons
        
        for chunk in selected:
            all_images.extend(chunk['images'])
            
            # Dédupliquer les sources en normalisant les URLs
            for source in chunk['sources']:
                # Normaliser: minuscules, sans espaces superflus
                source_normalized = source.lower().strip()
                
                # Si pas déjà vue, ajouter la source originale
                if source_normalized not in seen_sources:
                    all_sources.append(source)
                    seen_sources.add(source_normalized)
        
        unique_images = list(dict.fromkeys(all_images))[:10]
        unique_sources = all_sources[:5]  # Déjà dédupliqué
        
        return {
            'query': query,
            'context': '\n'.join(context_parts),
            'images': unique_images,
            'sources': unique_sources,
            'chunks_used': len(selected)
        }
    
    def search(self, query: str, top_k: int = 10) -> Dict:
        """
        Recherche complète optimisée
        
        Pipeline:
        1. Auto-détection entité + filtres
        2. Recherche vectorielle Pinecone
        3. Reranking hybride
        4. Déduplication
        5. Préparation contexte LLM
        """
        print(f"\n{'='*80}")
        print(f"🔍 RECHERCHE: {query}")
        print(f"{'='*80}")
        
        # 1. Filtres intelligents
        filter_dict, detected = self.build_smart_filter(query)
        
        if detected:
            print(f"🤖 Entité détectée:")
            if detected.get('subcategory'):
                print(f"   📁 Subcategory: {detected['subcategory']}")
            if detected.get('category'):
                print(f"   📂 Category: {detected['category']}")
            if detected.get('pole'):
                print(f"   📍 Pole: {detected['pole']}")
        
        if filter_dict:
            print(f"🔧 Filtres appliqués:")
            for key, value in filter_dict.items():
                print(f"   • {key} = {value['$eq']}")
        else:
            print(f"⚠️  Recherche globale (aucun filtre)")
        
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
                'chunk_index': metadata.get('chunk_index', 0),
                'images': images,
                'sources': sources
            })
        
        print(f"\n📊 PIPELINE:")
        print(f"   1️⃣ Pinecone brut: {len(results)} chunks")
        
        # 4. Reranking
        if results:
            results = self.rerank_results(results, query)
            print(f"   2️⃣ Après reranking: {len(results)} chunks")
        
        # 5. Déduplication
        if results:
            results = self.deduplicate_chunks(results)
            print(f"   3️⃣ Après déduplication: {len(results)} chunks")
        
        # 6. Contexte LLM
        llm_context = None
        if results:
            llm_context = self.prepare_llm_context(results, query)
            print(f"   4️⃣ Contexte LLM: {llm_context['chunks_used']} chunks, {len(llm_context['context'])} caractères")
        
        return {
            'results': results,
            'llm_context': llm_context,
            'query': query
        }


# =============================================================================
# AFFICHAGE DES RÉSULTATS
# =============================================================================

def display_results(search_result: Dict):
    """Affiche les résultats de manière claire"""
    
    results = search_result['results']
    llm_context = search_result['llm_context']
    
    if not results:
        print("\n❌ Aucun résultat trouvé")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 RÉSULTATS DÉTAILLÉS")
    print(f"{'='*80}")
    
    # Top 3 résultats
    for i, result in enumerate(results[:3], 1):
        print(f"\n{'─'*80}")
        print(f"📄 RÉSULTAT {i}")
        print(f"{'─'*80}")
        print(f"Pertinence: {result['score']*100:.1f}% (Pinecone) | {result.get('hybrid_score', 0)*100:.1f}% (Hybride)")
        print(f"Pole: {result['pole']}")
        print(f"Catégorie: {result['category']}")
        if result['subcategory']:
            print(f"Sous-catégorie: {result['subcategory']}")
        print(f"Fichier: {result['source_file']}")
        
        print(f"\n📝 Extrait:")
        print(f"   {result['text'][:300]}...")
        
        if result['images']:
            print(f"\n🖼️  Images ({len(result['images'])}):")
            for img in result['images'][:2]:
                print(f"   • {os.path.basename(img)}")
        
        if result['sources']:
            print(f"\n📚 Sources ({len(result['sources'])}):")
            for src in result['sources'][:2]:
                print(f"   • {src[:70]}...")
    
    # Contexte LLM
    if llm_context:
        print(f"\n{'='*80}")
        print(f"📦 CONTEXTE PRÉPARÉ POUR GEMINI")
        print(f"{'='*80}")
        print(f"Chunks utilisés: {llm_context['chunks_used']}")
        print(f"Images disponibles: {len(llm_context['images'])}")
        print(f"Sources disponibles: {len(llm_context['sources'])}")
        
        print(f"\n📝 Aperçu du contexte:")
        print(llm_context['context'][:500] + "...")
        
        if llm_context['images']:
            print(f"\n🖼️  Images à envoyer:")
            for img in llm_context['images'][:3]:
                print(f"   • {os.path.basename(img)}")
        
        if llm_context['sources']:
            print(f"\n📚 Sources à citer:")
            for src in llm_context['sources']:
                print(f"   • {src}")


# =============================================================================
# TESTS AUTOMATIQUES
# =============================================================================

def run_tests():
    """Exécute une batterie de tests"""
    
    print("🚀 TESTS DU SYSTÈME RAG OPTIMISÉ")
    print("="*80)
    
    # Initialiser le RAG
    rag = OptimizedBeninRAG(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )
    
    # Questions de test
    test_queries = [
        "Parle-moi du roi Ghézo",
        "Histoire des Amazones du Dahomey",
        "Temple des Pythons",
        "Musée Honmè Porto-Novo",
        "Route des Esclaves Ouidah",
    ]
    
    for query in test_queries:
        # Recherche
        result = rag.search(query, top_k=10)
        
        # Affichage
        display_results(result)
        
        print(f"\n{'='*80}\n")
        input("⏸️  Appuyez sur Entrée pour continuer au test suivant...\n")
    
    print("\n✅ TOUS LES TESTS TERMINÉS !")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    # Vérifier la configuration
    if not os.getenv("PINECONE_API_KEY"):
        print("❌ ERREUR: PINECONE_API_KEY non définie dans .env")
        print("Créez un fichier .env avec:")
        print("PINECONE_API_KEY=votre_cle")
        print("INDEX_NAME=benin-heritage")
        exit(1)
    
    # Lancer les tests
    run_tests()