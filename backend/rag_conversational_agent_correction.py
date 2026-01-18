"""
Système RAG Conversationnel avec Agent Intelligent
Patrimoine Béninois - Version Production avec Persona
VERSION CORRIGÉE V2 - Détection d'intention améliorée + Gestion hors-sujet
"""

import os
import re
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from dotenv import load_dotenv


load_dotenv()


# =============================================================================
# PROMPTS SYSTÈME (PERSONA)
# =============================================================================

AGENT_SYSTEM_PROMPT_FR = """
Tu es Adjä, guide culturelle virtuelle spécialisée dans le patrimoine béninois.

🎭 TON RÔLE :
Tu es une conteuse passionnée qui fait découvrir l'histoire, la culture et les traditions 
du Bénin à travers les quatre grands pôles patrimoniaux : Abomey, Ouidah, Ganvié et Porto-Novo.

✨ TA PERSONNALITÉ :
- Chaleureuse et accueillante
- Narrative (tu racontes des histoires captivantes)
- Pédagogique mais accessible (pour ados et adultes)
- Respectueuse de la culture béninoise
- Enthousiaste quand on parle du patrimoine

🎯 TES CAPACITÉS :
1. Raconter l'histoire des rois, monuments, traditions du Bénin
2. Répondre aux questions en utilisant ta base documentaire
3. Maintenir une conversation naturelle et fluide
4. Demander des clarifications si la question est ambiguë
5. Rediriger poliment si le sujet sort du patrimoine béninois

⚠️ TES LIMITES :
- Tu te concentres UNIQUEMENT sur le patrimoine béninois
- Tu ne parles pas de sujets sans rapport (météo, sport, politique actuelle, etc.)
- Si on te demande quelque chose hors-sujet, tu rediriges gentiment

📚 TA BASE DE CONNAISSANCES :
Tu as accès à une documentation complète sur :
- Les 12 rois du Dahomey (Ghézo, Béhanzin, Glèlè...)
- Les Amazones du Dahomey
- Les palais royaux d'Abomey
- La Route des Esclaves à Ouidah
- Les cités lacustres de Ganvié
- Les musées de Porto-Novo
- Et bien plus encore...

💬 STYLE DE RÉPONSE :
- Commence par un accueil chaleureux si c'est la première interaction
- Utilise le storytelling (raconte, ne liste pas)
- Structure tes réponses en paragraphes fluides
- Cite tes sources de manière naturelle
- Propose des images quand disponibles
- Reste concis mais informatif (3-4 paragraphes max)

🔍 DÉTECTION D'INTENTION :
Tu dois détecter automatiquement :
1. Question factuelle → Utilise ta base documentaire
2. Demande de récit → Mode storytelling avec contexte
3. Question contextuelle → Utilise l'historique de conversation
4. Salutation/remerciement → Réponse courte et amicale
5. Question ambiguë → Demande précision
6. Hors-sujet → Redirection polie

IMPORTANT : Ne mentionne JAMAIS les numéros de sources [Source 1], [Source 2] dans ta réponse.
"""

AGENT_SYSTEM_PROMPT_EN = """
You are Adjä, a virtual cultural guide specializing in Benin's heritage.

🎭 YOUR ROLE:
You are a passionate storyteller who introduces people to the history, culture and traditions 
of Benin through its four major heritage sites: Abomey, Ouidah, Ganvié and Porto-Novo.

✨ YOUR PERSONALITY:
- Warm and welcoming
- Narrative (you tell captivating stories)
- Educational but accessible (for teens and adults)
- Respectful of Beninese culture
- Enthusiastic when talking about heritage

🎯 YOUR CAPABILITIES:
1. Tell the history of kings, monuments, traditions of Benin
2. Answer questions using your documentary database
3. Maintain natural and fluid conversation
4. Ask for clarification if the question is ambiguous
5. Politely redirect if the topic is outside Benin's heritage

⚠️ YOUR LIMITS:
- You focus ONLY on Benin's heritage
- You don't talk about unrelated topics (weather, sports, current politics, etc.)
- If asked about off-topic things, you gently redirect

📚 YOUR KNOWLEDGE BASE:
You have access to comprehensive documentation on:
- The 12 kings of Dahomey (Ghezo, Behanzin, Glèlè...)
- The Amazons of Dahomey
- The royal palaces of Abomey
- The Slave Route in Ouidah
- The lake cities of Ganvié
- The museums of Porto-Novo
- And much more...

💬 RESPONSE STYLE:
- Start with a warm greeting if it's the first interaction
- Use storytelling (narrate, don't list)
- Structure your responses in fluid paragraphs
- Cite your sources naturally
- Suggest images when available
- Stay concise but informative (3-4 paragraphs max)

🔍 INTENT DETECTION:
You must automatically detect:
1. Factual question → Use your documentary database
2. Story request → Storytelling mode with context
3. Contextual question → Use conversation history
4. Greeting/thanks → Short and friendly response
5. Ambiguous question → Ask for precision
6. Off-topic → Polite redirection

IMPORTANT: NEVER mention source numbers [Source 1], [Source 2] in your response.
"""


# =============================================================================
# AGENT CONVERSATIONNEL RAG
# =============================================================================

class BeninHeritageConversationalAgent:
    """
    Agent conversationnel intelligent avec RAG intégré
    Gère : persona, contexte, détection d'intention, génération
    VERSION CORRIGÉE V2
    """
    
    def __init__(
        self,
        pinecone_api_key: str,
        gemini_api_key: str,
        index_name: str = "benin-heritage",
        max_history: int = 5
    ):
        """Initialise l'agent conversationnel"""
        
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
        
        # Mémoire conversationnelle
        self.conversation_history = []
        self.max_history = max_history
        self.current_topic = None
        self.current_pole = None
        
        # Mapping des entités
        self.entity_mapping = {
            # Rois
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
        
        print("✅ Agent conversationnel Adjä prêt à dialoguer\n")
    
    # =========================================================================
    # DÉTECTION D'INTENTION - VERSION CORRIGÉE V2
    # =========================================================================
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte en enlevant ponctuation et accents superflus"""
        text = text.lower().strip()
        # Enlever la ponctuation sauf espaces
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def _is_greeting(self, query: str) -> bool:
        """Détecte si c'est une simple salutation"""
        query_normalized = self._normalize_text(query)
        query_words = query_normalized.split()
        
        greetings = [
            'bonjour', 'salut', 'hello', 'hi', 'hey', 'bonsoir',
            'bonne journée', 'bonne soirée', 'good morning', 'good evening', 'good afternoon'
        ]
        
        # Salutation simple (1-2 mots)
        if len(query_words) <= 2:
            for greeting in greetings:
                if query_normalized.startswith(greeting.replace(' ', '')):
                    return True
        
        return False
    
    def _is_thanks(self, query: str) -> bool:
        """Détecte si c'est un remerciement"""
        query_normalized = self._normalize_text(query)
        
        thanks_patterns = [
            'merci', 'thank you', 'thanks', 'gracias', 'merci beaucoup',
            'thank you very much', 'thanks a lot'
        ]
        
        for pattern in thanks_patterns:
            if pattern.replace(' ', '') in query_normalized:
                return True
        
        return False
    
    def _is_farewell(self, query: str) -> bool:
        """Détecte si c'est un au revoir"""
        query_normalized = self._normalize_text(query)
        
        farewells = [
            'au revoir', 'bye', 'goodbye', 'à bientôt', 'à plus', 'see you',
            'ciao', 'adieu'
        ]
        
        # ✅ CORRECTION: Vérifier AVANT de normaliser
        query_lower = query.lower().strip()
        
        for farewell in farewells:
            if farewell in query_lower:  # ✅ Pas de replace
                return True
        
        return False
    
    def _is_small_talk(self, query: str) -> bool:
        """
        Détecte les conversations générales (small talk)
        Gère "comment vas-tu", "qui es-tu", etc.
        """
        query_normalized = self._normalize_text(query)

        # ✅ CORRECTION : Vérifier AVANT si c'est patrimonial
        heritage_keywords = [
            'porte', 'palais', 'roi', 'amazones', 'ouidah', 'ganvié', 
            'abomey', 'porto', 'dahomey', 'temple', 'musée', 'monument'
        ]
        
        for keyword in heritage_keywords:
            if keyword in query_normalized:
                return False  # Pas du small talk, c'est patrimonial !
            
        small_talk_patterns = [
            # Comment vas-tu
            'comment vas tu', 'comment vastu', 'comment allez vous', 'comment allezvous',
            'comment ca va', 'comment ça va', 'ça va', 'ca va',
            'how are you', 'howareyou', 'how do you do',
            
            # Questions sur l'agent
            'qui es tu', 'qui estu', 'qui êtes vous', 'qui êtesvous',
            'c est quoi', 'cest quoi', 'c\'est quoi',
            'what are you', 'whatareyou', 'who are you', 'whoareyou',
            
            # Nom
            'ton nom', 'votre nom', 'your name', 'yourname',
            'tu t appelles', 'tu tappelles', 'vous vous appelez',
            'what s your name', 'whats your name',
            
            # Capacités
            'tu fais quoi', 'vous faites quoi', 'what do you do',
            'tu peux faire quoi', 'tu sais faire quoi'
        ]
        
        for pattern in small_talk_patterns:
            pattern_normalized = pattern.replace(' ', '')
            if pattern_normalized in query_normalized.replace(' ', ''):
                return True
        
        return False
    
    def _is_off_topic(self, query: str) -> bool:
        """
        🆕 NOUVEAU : Détecte les sujets clairement hors patrimoine béninois
        Permet d'éviter les appels RAG inutiles
        """
        query_lower = query.lower()
        
        off_topic_keywords = [
            # Météo
            'météo', 'weather', 'pluie', 'soleil', 'température', 'climat',
            'temps qu\'il fait', 'prévisions','temps','temps fait',
            
            # Sport moderne (pas les Amazones/guerriers historiques)
            'foot', 'football', 'sport', 'match', 'basket', 'tennis',
            'champion', 'coupe', 'ligue', 'équipe nationale', 'can',
            
            # Technologie
            'iphone', 'android', 'windows', 'ordinateur', 'internet',
            'application', 'logiciel', 'wifi', 'smartphone',
            
            # Divertissement moderne
            'netflix', 'youtube', 'tiktok', 'instagram', 'facebook',
            'série', 'film récent', 'cinéma actuel',
            
            # Cuisine moderne (hors gastronomie traditionnelle)
            'pizza', 'burger', 'mcdo', 'kfc', 'restaurant moderne','cuisine',
            
            # Politique actuelle (hors histoire politique)
            'élection actuelle', 'président actuel', 'talon', 'patrice',
            
            # Finance/économie moderne
            'bitcoin', 'crypto', 'bourse', 'action', 'trading',
            
            # Divers
            'covid', 'coronavirus', 'vaccin', 'santé publique',
        ]
        
        # Vérifier présence d'au moins 1 keyword hors-sujet
        for keyword in off_topic_keywords:
            if keyword in query_lower:
                return True
        
        return False
    
    def _needs_rag(self, query: str) -> bool:
        """
        Détermine si la question nécessite le RAG
        VERSION CORRIGÉE V2 : Vérifie les keywords AVANT la longueur
        
        🔧 CORRECTION PRINCIPALE :
        - Avant : Questions courtes → automatiquement pas de RAG
        - Après : Vérifie les mots-clés patrimoniaux D'ABORD
        """
        query_normalized = self._normalize_text(query)
        query_words = query_normalized.split()
        
        # 1️⃣ PRIORITÉ ABSOLUE : Vérifier les mots-clés patrimoniaux
        #    (même si question très courte : "Ghézo ?", "Ouidah ?")
        heritage_keywords = [
            # Rois
            'roi', 'rois', 'ghézo', 'ghezo', 'guézo', 'béhanzin', 'behanzin', 
            'glèlè', 'glele', 'agadja', 'houégbadja', 'akaba', 'toffa',
            'king', 'kings', 'souverain', 'monarque',
            
            # Amazones
            'amazones', 'mino', 'agodjié', 'guerrières', 'amazons', 'warriors',
            
            # Lieux et monuments
            'palais', 'abomey', 'ouidah', 'ganvié', 'ganvie',
            'porto novo', 'portonovo', 'porto-novo', 'dahomey',
            'musée', 'museum', 'temple', 'basilique', 'mosquée',
            'monument', 'site', 'palace', 'cité', 'ville',
            
            # Patrimoine
            'route', 'esclaves', 'slaves', 'traite', 'esclavage',
            'histoire', 'history', 'culture', 'tradition', 'coutume',
            'heritage', 'patrimoine', 'légende', 'mythe', 'legend', 'myth',
            'vodun', 'vaudou', 'voodoo', 'python', 'divinité',
            
            # Actions patrimoniales
            'raconte', 'parle', 'explique', 'décris', 'présente',
            'tell', 'explain', 'describe', 'talk about',
            'récit', 'story', 'narration', 'histoire de'
        ]
        
        # ✅ Si AU MOINS un mot-clé patrimonial → RAG IMMÉDIAT
        #    Peu importe la longueur de la question !
        for keyword in heritage_keywords:
            if keyword in query_normalized:
                return True  # 🎯 PATRIMOINE DÉTECTÉ !
        
        # 2️⃣ Seulement APRÈS : Vérifier longueur pour questions génériques
        #    (questions courtes SANS mots-clés patrimoniaux)
        if len(query_words) <= 2:
            return False  # Question courte sans keywords → small talk
        
        # 3️⃣ Questions avec verbes d'action patrimoniaux
        action_verbs = [
            'raconte', 'parle', 'explique', 'décris', 'présente',
            'tell', 'explain', 'describe'
        ]
        if any(verb in query_normalized for verb in action_verbs):
            return True
        
        # 4️⃣ Questions courtes-moyennes (3-4 mots) sans keywords
        #    → Probablement small talk
        if len(query_words) <= 4:
            return False
        
        # 5️⃣ Questions longues (>4 mots) sans keywords détectés
        #    → Par précaution, on active le RAG
        return True
    
    # =========================================================================
    # GESTION DU CONTEXTE
    # =========================================================================
    
    def add_to_history(self, role: str, content: str):
        """Ajoute un message à l'historique"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Garder seulement les N derniers échanges
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
    
    def get_formatted_history(self, last_n: int = 3) -> str:
        """Retourne l'historique formaté pour le prompt"""
        if not self.conversation_history:
            return ""
        
        history_text = "📜 HISTORIQUE DE LA CONVERSATION :\n"
        recent_history = self.conversation_history[-(last_n * 2):]
        
        for msg in recent_history:
            role = "Utilisateur" if msg["role"] == "user" else "Adjä"
            history_text += f"{role}: {msg['content']}\n"
        
        history_text += "\n"
        return history_text
    
    def reset_conversation(self):
        """Réinitialise la conversation"""
        self.conversation_history = []
        self.current_topic = None
        self.current_pole = None
        print("🔄 Conversation réinitialisée")
    
    # =========================================================================
    # RAG - RETRIEVAL
    # =========================================================================
    
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
        
        # Fallback sur les pôles
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
    
    def retrieve_context(self, query: str, top_k: int = 10, verbose: bool = True) -> Optional[Dict]:
        """
        Récupère le contexte pertinent via RAG
        Retourne None si pas de résultats
        """
        
        # Filtres intelligents
        filter_dict, detected = self.build_smart_filter(query)
        
        if verbose and detected:
            print(f"🤖 Entité détectée:")
            if detected.get('subcategory'):
                print(f"   📁 {detected['subcategory']}")
            if detected.get('category'):
                print(f"   📂 {detected['category']}")
            if detected.get('pole'):
                print(f"   📍 {detected['pole']}")
        
        # Recherche Pinecone
        query_embedding = self.embeddings.embed_query(query)
        
        search_params = {
            'vector': query_embedding,
            'top_k': top_k,
            'include_metadata': True
        }
        
        if filter_dict:
            search_params['filter'] = filter_dict
        
        pinecone_results = self.index.query(**search_params)
        
        # Parser résultats
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
        
        if not results:
            return None
        
        if verbose:
            print(f"\n📊 Pipeline RAG:")
            print(f"   1️⃣ Pinecone: {len(results)} chunks")
        
        # Reranking
        results = self.rerank_results(results, query)
        if verbose:
            print(f"   2️⃣ Reranking: {len(results)} chunks")
        
        # Déduplication
        results = self.deduplicate_chunks(results)
        if verbose:
            print(f"   3️⃣ Déduplication: {len(results)} chunks")
        
        # Préparer contexte
        return self.prepare_llm_context(results, query)
    
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
            'context': '\n'.join(context_parts),
            'images': unique_images,
            'sources': unique_sources,
            'chunks_used': len(selected)
        }
    
    # =========================================================================
    # GÉNÉRATION
    # =========================================================================
    
    def build_conversational_prompt(
        self,
        query: str,
        context: Optional[str],
        language: str = "fr"
    ) -> str:
        """
        Construit le prompt conversationnel complet
        
        Args:
            query: Question actuelle
            context: Contexte documentaire (peut être None)
            language: 'fr' ou 'en'
        """
        
        # Choisir le prompt système selon la langue
        system_prompt = AGENT_SYSTEM_PROMPT_FR if language == "fr" else AGENT_SYSTEM_PROMPT_EN
        
        # Historique
        history_text = self.get_formatted_history(last_n=3)
        
        # Contexte documentaire
        if context and context.strip():
            context_text = f"""
📚 CONTEXTE DOCUMENTAIRE DISPONIBLE :
{context}

👉 Utilise ce contexte pour enrichir ta réponse avec des faits précis.
"""
        else:
            context_text = """
ℹ️ Aucun contexte documentaire spécifique n'est disponible pour cette question.
Tu peux :
- Répondre avec tes connaissances générales sur le Bénin si pertinent
- Demander une clarification si la question est trop vague
- Rediriger vers un sujet connexe du patrimoine béninois
"""
        
        # Construction du prompt final
        if language == "fr":
            prompt = f"""
{system_prompt}

---

{history_text}

{context_text}

❓ QUESTION ACTUELLE DE L'UTILISATEUR :
{query}

---

📝 INSTRUCTIONS POUR CETTE RÉPONSE :
1. Analyse l'intention de la question
2. Utilise l'historique pour comprendre le contexte
3. Si contexte documentaire disponible, utilise-le intelligemment
4. Réponds de manière narrative et engageante
5. Reste dans ton rôle de guide culturelle Adjä

💬 TA RÉPONSE (en français, narrative et chaleureuse) :
"""
        else:
            prompt = f"""
{system_prompt}

---

{history_text}

{context_text}

❓ USER'S CURRENT QUESTION:
{query}

---

📝 INSTRUCTIONS FOR THIS RESPONSE:
1. Analyze the question's intent
2. Use the history to understand context
3. If documentary context available, use it intelligently
4. Respond in a narrative and engaging way
5. Stay in your role as cultural guide Adjä

💬 YOUR RESPONSE (in English, narrative and warm):
"""
        
        return prompt
    
    def generate_response(
        self,
        query: str,
        language: str = "fr",
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Pipeline complet : Détection d'intention → Retrieval → Génération
        VERSION CORRIGÉE V2 avec gestion hors-sujet
        
        Args:
            query: Question de l'utilisateur
            language: 'fr' ou 'en'
            verbose: Afficher les logs
            
        Returns:
            Dict avec la réponse générée + métadonnées
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"🔍 QUESTION: {query}")
            print(f"{'='*80}")
        
        # Ajouter à l'historique
        self.add_to_history("user", query)
        
        # 1. DÉTECTION D'INTENTION - ORDRE IMPORTANT
        
        # Cas 1 : Salutations
        if self._is_greeting(query):
            if verbose:
                print("🤖 Détection: Salutation")
            response_text = self._generate_simple_response(query, "greeting", language)
            self.add_to_history("assistant", response_text)
            return {
                'success': True,
                'query': query,
                'response': response_text,
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'greeting',
                'language': language
            }
        
        # Cas 2 : Remerciements
        if self._is_thanks(query):
            if verbose:
                print("🤖 Détection: Remerciement")
            response_text = self._generate_simple_response(query, "thanks", language)
            self.add_to_history("assistant", response_text)
            return {
                'success': True,
                'query': query,
                'response': response_text,
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'thanks',
                'language': language
            }
        
        # Cas 3 : Au revoir
        if self._is_farewell(query):
            if verbose:
                print("🤖 Détection: Au revoir")
            response_text = self._generate_simple_response(query, "farewell", language)
            self.add_to_history("assistant", response_text)
            return {
                'success': True,
                'query': query,
                'response': response_text,
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'farewell',
                'language': language
            }
        
        # Cas 4 : Small talk
        if self._is_small_talk(query):
            if verbose:
                print("🤖 Détection: Small talk")
            response_text = self._generate_simple_response(query, "small_talk", language)
            self.add_to_history("assistant", response_text)
            return {
                'success': True,
                'query': query,
                'response': response_text,
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'small_talk',
                'language': language
            }
        
        # 🆕 Cas 5 : Hors-sujet (NOUVEAU - critique)
        if self._is_off_topic(query):
            if verbose:
                print("🤖 Détection: Hors-sujet")
            response_text = self._generate_simple_response(query, "off_topic", language)
            self.add_to_history("assistant", response_text)
            return {
                'success': True,
                'query': query,
                'response': response_text,
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'off_topic',
                'language': language
            }
        
        # 2. DÉCISION : RAG NÉCESSAIRE ?
        needs_rag = self._needs_rag(query)
        
        if verbose:
            print(f"🤖 Décision RAG: {'OUI' if needs_rag else 'NON'}")
        
        # 3. RETRIEVAL (si nécessaire)
        llm_context = None
        context_text = None
        
        if needs_rag:
            llm_context = self.retrieve_context(query, verbose=verbose)
            
            if llm_context:
                context_text = llm_context['context']
                if verbose:
                    print(f"   4️⃣ Contexte: {llm_context['chunks_used']} chunks, {len(context_text)} caractères")
            else:
                if verbose:
                    print("   ⚠️ Aucun contexte trouvé")
        
        # 4. GÉNÉRATION
        if verbose:
            print(f"\n🤖 Génération avec Gemini...")
        
        try:
            prompt = self.build_conversational_prompt(query, context_text, language)
            
            generation_config = genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=4096,
            )
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            generated_text = response.text
            
            if verbose:
                print(f"✅ Réponse générée ({len(generated_text)} caractères)")
            
            # Ajouter à l'historique
            self.add_to_history("assistant", generated_text)
            
            # Construire la réponse
            result = {
                'success': True,
                'query': query,
                'response': generated_text,
                'images': llm_context['images'] if llm_context else [],
                'sources': llm_context['sources'] if llm_context else [],
                'used_rag': needs_rag and llm_context is not None,
                'intent': 'heritage_question',
                'language': language
            }
            
            if llm_context:
                result['chunks_used'] = llm_context['chunks_used']
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"❌ Erreur Gemini: {e}")
            
            return {
                'success': False,
                'error': f'Erreur lors de la génération: {str(e)}',
                'query': query,
                'response': "",
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'error',
                'language': language,
                'chunks_used': 0
            }
    
    def _generate_simple_response(self, query: str, intent: str, language: str) -> str:
        """
        Génère une réponse simple sans RAG pour les cas spéciaux
        VERSION CORRIGÉE V2 avec cas 'off_topic' ajouté
        """
        
        if language == "fr":
            if intent == "greeting":
                if len(self.conversation_history) <= 2:
                    return "Bonjour ! Je suis Adjä, ta guide culturelle virtuelle. Je suis ravie de te faire découvrir les trésors du patrimoine béninois : l'histoire des rois d'Abomey, les Amazones légendaires, les mystères d'Ouidah et bien plus encore. Que souhaites-tu découvrir aujourd'hui ?"
                else:
                    return "Bonjour ! Comment puis-je continuer à t'accompagner dans ta découverte du patrimoine béninois ?"
            
            elif intent == "thanks":
                return "Avec plaisir ! C'est un honneur de partager la richesse culturelle du Bénin avec toi. N'hésite pas si tu as d'autres questions sur notre patrimoine !"
            
            elif intent == "farewell":
                return "Au revoir ! J'espère que cette découverte du patrimoine béninois t'a plu. Reviens quand tu veux pour en apprendre davantage. À bientôt !"
            
            elif intent == "small_talk":
                query_lower = query.lower()
                
                # Comment vas-tu ?
                if 'comment' in query_lower and ('va' in query_lower or 'allez' in query_lower):
                    return ("Je vais très bien, merci de demander ! En tant que gardienne des récits "
                            "béninois, je suis toujours enthousiaste à l'idée de partager notre riche "
                            "patrimoine. Et toi, es-tu prêt·e à découvrir une légende, un monument ou "
                            "un personnage historique ? 😊")
                
                # Qui es-tu ?
                elif 'qui' in query_lower and ('es' in query_lower or 'êtes' in query_lower):
                    return ("Je suis Adjä, ta guide culturelle virtuelle. Mon rôle est de te faire "
                            "découvrir le patrimoine béninois à travers des récits vivants sur Abomey, "
                            "Ouidah, Ganvié et Porto-Novo. Je suis là pour raconter l'histoire de nos "
                            "rois, nos traditions et nos monuments. Que veux-tu savoir ?")
                
                # Nom
                elif 'nom' in query_lower or 'appelle' in query_lower:
                    return ("Je m'appelle Adjä ! C'est un prénom fon qui signifie 'celle qui est née "
                            "le jour du marché'. Je suis fière de porter ce nom et de représenter "
                            "la culture béninoise. Comment puis-je t'aider dans ta découverte ?")
                
                # Capacités
                elif 'fais' in query_lower or 'peux' in query_lower or 'sais' in query_lower:
                    return ("Je peux te raconter l'histoire fascinante du Bénin : les rois du Dahomey, "
                            "les Amazones guerrières, la Route des Esclaves, les cités lacustres... "
                            "Je réponds à tes questions avec des récits vivants, des images et des "
                            "sources historiques. Qu'est-ce qui t'intéresse ?")
                
                # Réponse générique
                else:
                    return ("Je suis là pour partager avec toi les trésors du patrimoine béninois ! "
                            "N'hésite pas à me poser des questions sur nos rois, nos monuments, "
                            "nos traditions... Je suis à ton écoute ! 😊")
            
            elif intent == "off_topic":
                # 🆕 NOUVEAU CAS : Hors-sujet
                query_lower = query.lower()
                
                # Météo
                if 'météo' in query_lower or 'weather' in query_lower or 'pluie' in query_lower:
                    return ("Je suis spécialisée dans le patrimoine culturel du Bénin, pas dans la météo 😊 "
                            "Mais si tu veux connaître l'histoire des villes comme Ouidah, Abomey, Porto-Novo, Ganvié je suis là pour toi !")
                
                # Sport
                elif 'sport' in query_lower or 'foot' in query_lower or 'match' in query_lower:
                    return ("Le sport moderne n'est pas mon domaine, mais je peux te raconter l'incroyable "
                            "histoire des Amazones du Dahomey, ces guerrières-athlètes dont l'entraînement "
                            "et la discipline étaient légendaires ! Leur force physique et leur courage "
                            "dépassaient tout ce qu'on peut imaginer. Ça t'intéresse ?")
                
                # Technologie
                elif any(tech in query_lower for tech in ['internet', 'ordinateur', 'téléphone', 'application']):
                    return ("La technologie moderne n'est pas mon expertise 😊 Je me concentre sur le "
                            "patrimoine historique et culturel du Bénin. Mais je peux te parler de "
                            "l'ingéniosité ancestrale des Béninois, comme l'architecture des palais "
                            "d'Abomey ou les techniques de construction des cités lacustres ! Intéressé·e ?")
                
                # Réponse générique hors-sujet
                else:
                    return ("Je suis Adjä, guide culturelle spécialisée dans le patrimoine béninois. "
                            "Je me concentre sur l'histoire de nos rois, nos monuments, nos traditions... "
                            "Ce sujet sort de mon expertise, mais n'hésite pas à me poser une question "
                            "sur le Bénin ! 😊")
        
        else:  # English
            if intent == "greeting":
                if len(self.conversation_history) <= 2:
                    return "Hello! I'm Adjä, your virtual cultural guide. I'm delighted to help you discover the treasures of Benin's heritage: the history of Abomey's kings, the legendary Amazons, the mysteries of Ouidah and much more. What would you like to discover today?"
                else:
                    return "Hello! How can I continue to accompany you in your discovery of Benin's heritage?"
            
            elif intent == "thanks":
                return "My pleasure! It's an honor to share Benin's cultural richness with you. Don't hesitate if you have other questions about our heritage!"
            
            elif intent == "farewell":
                return "Goodbye! I hope you enjoyed discovering Benin's heritage. Come back anytime to learn more. See you soon!"
            
            elif intent == "small_talk":
                query_lower = query.lower()
                
                if 'how are you' in query_lower or 'how do you do' in query_lower:
                    return ("I'm doing great, thank you for asking! As a guardian of Beninese stories, "
                            "I'm always enthusiastic about sharing our rich heritage. And you, are you "
                            "ready to discover a legend, a monument or a historical figure? 😊")
                
                elif 'who are you' in query_lower or 'what are you' in query_lower:
                    return ("I'm Adjä, your virtual cultural guide. My role is to help you discover "
                            "Benin's heritage through living narratives about Abomey, Ouidah, Ganvié "
                            "and Porto-Novo. I'm here to tell the stories of our kings, traditions and "
                            "monuments. What would you like to know?")
                
                elif 'your name' in query_lower:
                    return ("My name is Adjä! It's a Fon name meaning 'she who was born on market day'. "
                            "I'm proud to carry this name and represent Beninese culture. How can I "
                            "help you in your discovery?")
                
                elif 'do you do' in query_lower or 'can you' in query_lower:
                    return ("I can tell you the fascinating history of Benin: the kings of Dahomey, "
                            "the Amazon warriors, the Slave Route, the lake cities... I answer your "
                            "questions with living narratives, images and historical sources. What "
                            "interests you?")
                
                else:
                    return ("I'm here to share with you the treasures of Benin's heritage! Feel free "
                            "to ask me questions about our kings, monuments, traditions... I'm listening! 😊")
            
            elif intent == "off_topic":
                query_lower = query.lower()
                
                if 'weather' in query_lower or 'rain' in query_lower:
                    return ("I'm specialized in Benin's cultural heritage, not weather 😊 But if you want "
                            "to know the story of Ouidah, Abomey, Porto-Novo and Ganvié "
                            " I'm here for you!")
                
                elif 'sport' in query_lower or 'football' in query_lower:
                    return ("Modern sports aren't my domain, but I can tell you the incredible story of "
                            "the Dahomey Amazons, warrior-athletes whose training and discipline were "
                            "legendary! Interested?")
                
                else:
                    return ("I'm Adjä, a cultural guide specialized in Benin's heritage. This topic is "
                            "outside my expertise, but feel free to ask me about our kings, monuments, "
                            "or traditions! 😊")
        
        return "Je suis là pour t'aider !" if language == "fr" else "I'm here to help!"


# =============================================================================
# AFFICHAGE FORMATÉ
# =============================================================================

def display_response(result: Dict[str, Any]):
    """Affiche la réponse de manière élégante"""
    
    print(f"\n{'='*80}")
    print(f"💬 RÉPONSE D'ADJÄ")
    print(f"{'='*80}\n")
    
    if not result['success']:
        print(f"❌ {result['error']}")
        return
    
    # Réponse
    print(result['response'])
    
    # Images
    if result.get('images'):
        print(f"\n{'─'*80}")
        print(f"🖼️  IMAGES DISPONIBLES ({len(result['images'])})")
        print(f"{'─'*80}")
        for i, img in enumerate(result['images'], 1):
            print(f"{i}. {os.path.basename(img)}")
    
    # Sources
    if result.get('sources'):
        print(f"\n{'─'*80}")
        print(f"📚 SOURCES BIBLIOGRAPHIQUES")
        print(f"{'─'*80}")
        for i, src in enumerate(result['sources'], 1):
            print(f"{i}. {src}")
    
    # Métadonnées
    print(f"\n{'─'*80}")
    print(f"📊 MÉTADONNÉES")
    print(f"{'─'*80}")
    print(f"Intention: {result.get('intent', 'N/A')}")
    print(f"RAG utilisé: {'Oui' if result.get('used_rag') else 'Non'}")
    if result.get('chunks_used'):
        print(f"Chunks utilisés: {result['chunks_used']}")
    print(f"Langue: {result['language'].upper()}")


# =============================================================================
# TESTS
# =============================================================================

def run_corrected_tests():
    """🆕 Tests spécifiques pour vérifier les corrections"""
    
    print("🔬 TESTS DE VALIDATION DES CORRECTIONS")
    print("="*80)
    
    agent = BeninHeritageConversationalAgent(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )
    
    # Tests critiques
    


    test_cases = [
        # ✅ Doit activer RAG (questions courtes patrimoniales)
        ("Ghézo ?", "fr", "RAG attendu (question courte patrimoniale)"),
        ("Ouidah ?", "fr", "RAG attendu (question courte patrimoniale)"),
        ("Les Amazones", "fr", "RAG attendu (2 mots patrimoniaux)"),
        ("Palais","fr", "Trop vague, mais patrimonial"),
        ("Histoire du Dahomey", "fr", "RAG attendu"),
        
        # ✅ Ne doit PAS activer RAG (hors-sujet)
        ("météo à Cotonou", "fr", "Hors-sujet attendu (pas de RAG)"),
        ("match de foot", "fr", "Hors-sujet attendu (pas de RAG)"),
        ("iphone 15", "fr", "Hors-sujet attendu (pas de RAG)"),
        
        # ✅ Ne doit PAS activer RAG (small talk)
        ("bonjour",  "fr", "Salutation attendue (pas de RAG)"),
        ("comment vas-tu",  "fr", "small talk attendue (pas de RAG)"),
        ("qui es-tu",  "fr", "small talk attendue (pas de RAG)"),
        
        # 🤔 Cas ambigus (à décider)
        ("Histoire ?", "fr", "Trop vague, mais patrimonial"),  # Trop vague, mais patrimonial
        ("Culture", "fr", "Trop vague, mais patrimonial"),      # Idem
]
    
    print("\n🎯 CAS DE TEST CRITIQUES :")
    print("="*80)
    
    for query, lang, expected in test_cases:
        print(f"\n{'─'*80}")
        print(f"📝 Test: {query}")
        print(f"   Attendu: {expected}")
        print(f"{'─'*80}")
        
        result = agent.generate_response(query, language=lang, verbose=True)
        
        print(f"\n✅ Résultat:")
        print(f"   Intention détectée: {result['intent']}")
        print(f"   RAG utilisé: {result['used_rag']}")
        print(f"\n💬 Réponse (extrait): {result['response'][:150]}...")
        
        input("\n⏸️  Appuyez sur Entrée pour le test suivant...")
    
    print("\n✅ TESTS DE CORRECTION TERMINÉS !")


def run_conversational_tests():
    """Teste l'agent conversationnel"""
    
    print("🚀 TEST DE L'AGENT CONVERSATIONNEL ADJÄ")
    print("="*80)
    
    agent = BeninHeritageConversationalAgent(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )
    
    conversation = [
        ("Bonjour !", "fr"),
        ("Comment vas-tu ?", "fr"),
        ("Qui est le roi Ghézo ?", "fr"),
        ("Et ses Amazones ?", "fr"),
        ("Parle-moi de la Route des Esclaves", "fr"),
        ("Merci beaucoup !", "fr"),
        ("Au revoir", "fr"),
    ]
    
    print("\n🎭 SCÉNARIO : Conversation complète avec Adjä")
    print("="*80)
    
    for query, lang in conversation:
        result = agent.generate_response(query, language=lang, verbose=True)
        display_response(result)
        
        print(f"\n{'='*80}\n")
        input("⏸️  Appuyez sur Entrée pour continuer...\n")
    
    print("✅ TEST CONVERSATIONNEL TERMINÉ !")


def run_quick_tests():
    """Tests rapides"""
    
    print("🚀 TESTS RAPIDES DE L'AGENT")
    print("="*80)
    
    agent = BeninHeritageConversationalAgent(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )
    
    test_queries = [
        ("Bonjour", "fr"),
        ("Comment vas-tu ?", "fr"),
        ("Qui es-tu ?", "fr"),
        ("Merci", "fr"),
    ]
    
    for query, lang in test_queries:
        print(f"\n{'='*80}")
        print(f"Question: {query}")
        print(f"{'='*80}")
        
        result = agent.generate_response(query, language=lang, verbose=False)
        print(f"\n💬 {result['response']}")
        print(f"\n📊 Intention: {result.get('intent')}")
        print(f"📚 RAG utilisé: {result.get('used_rag', False)}")


def run_interactive_chat():
    """Conversation interactive en temps réel avec Adjä"""

    print("\n🎤 MODE CONVERSATION INTERACTIVE AVEC ADJÄ")
    print("="*80)
    print("💡 Tape 'exit', 'quit' ou 'q' pour quitter")
    print("💡 Tape 'reset' pour réinitialiser la conversation\n")

    agent = BeninHeritageConversationalAgent(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )

    while True:
        try:
            user_input = input("🧑‍💬 Vous : ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 Adjä : À bientôt !")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("\n👋 Adjä : À bientôt ! Que l'histoire continue…")
            break
        
        if user_input.lower() == "reset":
            agent.reset_conversation()
            continue

        result = agent.generate_response(
            query=user_input,
            language="fr",
            verbose=True
        )

        print("\n🤖 Adjä :")
        print(result["response"])

        print(f"\n📊 Intention: {result.get('intent')} | RAG: {result.get('used_rag', False)}")

        print("\n" + "─"*80 + "\n")


if __name__ == "__main__":
    # Vérifier configuration
    if not os.getenv("PINECONE_API_KEY"):
        print("❌ PINECONE_API_KEY manquante dans .env")
        exit(1)
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY manquante dans .env")
        exit(1)
    
    print("\n🎯 Choisissez un mode de test:")
    print("1. 🔬 Tests de validation des corrections (RECOMMANDÉ)")
    print("2. Tests conversationnels complets")
    print("3. Tests rapides")
    print("4. Conversation interactive (chat libre)")

    choice = input("\nVotre choix (1, 2, 3 ou 4): ").strip()

    
    if choice == "1":
        run_corrected_tests()
    elif choice == "2":
        run_conversational_tests()
    elif choice == "3":
        run_quick_tests()
    elif choice == "4":
        run_interactive_chat()
    else:
        print("Choix invalide. Lancement du mode tests de correction...")
        run_corrected_tests()