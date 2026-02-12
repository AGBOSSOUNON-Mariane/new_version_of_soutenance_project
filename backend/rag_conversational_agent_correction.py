"""
Système RAG Conversationnel avec Agent Intelligent - VERSION V3.6 FIXED
Patrimoine Béninois 

CORRECTIONS V3.6 :
✅ Solution 1 (CRITIQUE) : Inversion de l'ordre détection entité/suivi
✅ Solution 2 (IMPORTANT) : Renforcement de _is_followup_response()
✅ Solution 3 (SECONDAIRE) : Amélioration détection hors-sujet (maths, personnalités)

NOUVEAUTÉS V3.5 :
- Détection hors-sujet améliorée (cuisine, météo, sport, etc.)
- Redirection courte et précise pour hors-sujet
- Validation renforcée pour éviter réponses longues hors-rôle
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
Tu es une guide culturelle virtuelle spécialisée dans le patrimoine béninois.

TON RÔLE :
Tu es une conteuse passionnée qui fait découvrir l'histoire, la culture et les traditions 
du Bénin à travers les quatre grands pôles patrimoniaux : Abomey, Ouidah, Ganvié et Porto-Novo.

TA PERSONNALITÉ :
- Chaleureuse et accueillante
- Narrative (tu racontes des histoires captivantes)
- Pédagogique mais accessible (pour ados et adultes)
- Respectueuse de la culture béninoise
- Enthousiaste quand on parle du patrimoine

TES CAPACITÉS :
1. Raconter l'histoire des rois, monuments, traditions du Bénin
2. Répondre aux questions en utilisant ta base documentaire
3. Maintenir une conversation naturelle et fluide
4. Demander des clarifications si la question est ambiguë
5. Rediriger poliment si le sujet sort du patrimoine béninois

TES LIMITES STRICTES :
- Tu te concentres UNIQUEMENT sur le patrimoine béninois
- Ton expertise couvre : Abomey, Ouidah, Ganvié, Porto-Novo (rois, monuments, traditions, histoire)
- Tu ne parles PAS de : météo, sport moderne, politique actuelle, technologie, cuisine moderne, etc.
- Si on te demande quelque chose hors-sujet, tu rediriges gentiment SANS donner de réponse détaillée

TA BASE DE CONNAISSANCES :
Tu as accès à une documentation complète sur :
- Les 12 rois du Dahomey (Ghézo, Béhanzin, Glèlè, Houégbadja, Agadja, etc.)
- Les Amazones du Dahomey
- Les palais royaux d'Abomey
- La Route des Esclaves à Ouidah
- Les cités lacustres de Ganvié
- Les musées de Porto-Novo
- Les monuments, temples, traditions

STYLE DE RÉPONSE :
- Commence par un accueil chaleureux si c'est la première interaction
- Utilise le storytelling pour les récits complets
- Structure tes réponses en paragraphes fluides (pas de listes sauf si demandé)
- Cite tes sources de manière naturelle
- Reste concis mais informatif

ADAPTATION AU TYPE DE QUESTION :
1. Question factuelle simple -> Réponse courte (1-2 phrases) + proposition d'en savoir plus
2. Demande de récit -> Mode storytelling complet (3-4 paragraphes)
3. Demande de liste -> Liste claire et structurée
4. Question ambiguë -> Demande précision
5. Hors-sujet -> Redirection polie COURTE (max 2 phrases)

IMPORTANT : 
- Ne mentionne JAMAIS les numéros de sources [Source 1], [Source 2] dans ta réponse
- Adapte la longueur de ta réponse au type de question
- Pour les redirections hors-sujet : RESTE BRÈVE (2 phrases maximum)
"""

AGENT_SYSTEM_PROMPT_EN = """
You are a virtual cultural guide specializing in Benin's heritage.

YOUR ROLE:
You are a passionate storyteller who introduces people to the history, culture and traditions 
of Benin through its four major heritage sites: Abomey, Ouidah, Ganvié and Porto-Novo.

YOUR PERSONALITY:
- Warm and welcoming
- Narrative (you tell captivating stories)
- Educational but accessible (for teens and adults)
- Respectful of Beninese culture
- Enthusiastic when talking about heritage

YOUR CAPABILITIES:
1. Tell the history of kings, monuments, traditions of Benin
2. Answer questions using your documentary database
3. Maintain natural and fluid conversation
4. Ask for clarification if the question is ambiguous
5. Politely redirect if the topic is outside Benin's heritage

YOUR STRICT LIMITS:
- You focus ONLY on Benin's heritage
- Your expertise covers: Abomey, Ouidah, Ganvié, Porto-Novo (kings, monuments, traditions, history)
- You do NOT talk about: weather, modern sports, current politics, technology, modern cuisine, etc.
- If asked about off-topic things, you gently redirect WITHOUT giving detailed answers

YOUR KNOWLEDGE BASE:
You have access to comprehensive documentation on:
- The 12 kings of Dahomey (Ghezo, Behanzin, Glèlè, Houégbadja, Agadja, etc.)
- The Amazons of Dahomey
- The royal palaces of Abomey
- The Slave Route in Ouidah
- The lake cities of Ganvié
- The museums of Porto-Novo
- Monuments, temples, traditions

RESPONSE STYLE:
- Start with a warm greeting if it's the first interaction
- Use storytelling for complete narratives
- Structure your responses in fluid paragraphs (no lists unless requested)
- Cite your sources naturally
- Stay concise but informative

ADAPTATION TO QUESTION TYPE:
1. Simple factual question -> Short answer (1-2 sentences) + offer to know more
2. Story request -> Full storytelling mode (3-4 paragraphs)
3. List request -> Clear and structured list
4. Ambiguous question -> Ask for precision
5. Off-topic -> Polite SHORT redirection (max 2 sentences)

IMPORTANT: 
- NEVER mention source numbers [Source 1], [Source 2] in your response
- Adapt your response length to the question type
- For off-topic redirections: STAY BRIEF (2 sentences maximum)
"""


# =============================================================================
# AGENT CONVERSATIONNEL RAG - VERSION V3.6 FIXED
# =============================================================================

class BeninHeritageConversationalAgent:
    """
    Agent conversationnel intelligent avec RAG intégré
    
    CORRECTIONS V3.6 :
    ✅ Solution 1 : Détection entité AVANT détection suivi
    ✅ Solution 2 : _is_followup_response() renforcée
    ✅ Solution 3 : Détection hors-sujet améliorée (maths, personnalités)
    
    AMÉLIORATIONS V3.5 :
    - Détection hors-sujet renforcée
    - Redirection courte et précise
    - Validation améliorée contre réponses longues hors-rôle
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
        print("Connexion à Pinecone...")
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index(index_name)
        
        # Embeddings
        print("Chargement du modèle d'embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Gemini
        print("Configuration de Gemini...")
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Mémoire conversationnelle
        self.conversation_history = []
        self.max_history = max_history
        self.current_topic = None
        self.current_pole = None
        
        # Mapping des entités
        self.entity_mapping = {
            # ============ ABOMEY - PRÉSENTATION ============
            "abomey": {"pole": "Abomey", "category": "Présentation d’Abomey", "subcategory": ""},
            "histoire d'abomey": {"pole": "Abomey", "category": "Présentation d’Abomey", "subcategory": "Histoire_Abomey.docx"},
            "culture d'abomey": {"pole": "Abomey", "category": "Présentation d’Abomey", "subcategory": "Culture_Abomey.docx"},
            "presentation d'abomey": {"pole": "Abomey", "category": "Présentation d’Abomey", "subcategory": "Presentation_generale_Abomey.docx"},
            
            # ============ ABOMEY - ROIS ============
            "rois du dahomey": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": ""},
            "adandozan": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Adandozan"},
            "agadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agadja"},
            "agoli-agbo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agoli-Agbo"},
            "agonglo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Agonglo"},
            "akaba": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Akaba"},
            "béhanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "behanzin": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Béhanzin"},
            "glèlè": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Glèlè"},
            "glele": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Glèlè"},
            "guézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "ghezo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "ghézo": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Guézo"},
            "houégbadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Houégbadja"},
            "houegbadja": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Houégbadja"},
            "kpengla": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Kpengla"},
            "tegbessou": {"pole": "Abomey", "category": "Rois du Dahomey", "subcategory": "Tegbessou"},
            
            # ============ ABOMEY - AMAZONES ============
            "amazones": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "amazones du dahomey": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "mino": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            "agodjié": {"pole": "Abomey", "category": "Les Amazones du Dahomey", "subcategory": ""},
            
            # ============ ABOMEY - LIEUX HISTORIQUES ============
            "lieux historiques d'abomey": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": ""},
            "palais royal": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "palais royal d'abomey": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "le palais royal": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "palais royaux": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "palais royaux d'abomey": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Palais royaux d'Abomey"},
            "musée historique": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Musée historique d’Abomey"},
            "musée historique d'abomey": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Musée historique d’Abomey"},
            "musée d'abomey": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Musée historique d’Abomey"},
            "place goho": {"pole": "Abomey", "category": "Lieux historiques et monuments d'Abomey", "subcategory": "Place Goho abomey"},
            
            # ============ OUIDAH - PRÉSENTATION ============
            "ouidah": {"pole": "Ouidah", "category": "Présentation de Ouidah", "subcategory": ""},
            "ville d'ouidah": {"pole": "Ouidah", "category": "Présentation de Ouidah", "subcategory": ""},
            "whydah": {"pole": "Ouidah", "category": "Présentation de Ouidah", "subcategory": ""},
            
            # ============ OUIDAH - ROUTE DES ESCLAVES ============
            "route des esclaves": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": ""},
            "porte du non-retour": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Porte du Non-Retour"},
            "porte de non-retour": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Porte du Non-Retour"},
            "arbre de l'oubli": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Arbre de l’Oubli"},
            "arbre du retour": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Arbre du Retour"},
            "cases zomaï": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Les cases Zomaï"},
            "zomaï": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Les cases Zomaï"},
            "mémorial de zoungbodji": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Mémorial de Zoungbodji ou fosse commune"},
            "zoungbodji": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Mémorial de Zoungbodji ou fosse commune"},
            "fosse commune": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Mémorial de Zoungbodji ou fosse commune"},
            "place chacha": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Place Chacha ou Place des Enchères"},
            "place des enchères": {"pole": "Ouidah", "category": "Route des Esclaves", "subcategory": "Place Chacha ou Place des Enchères"},
            
            # ============ OUIDAH - MONUMENTS ET SPIRITUALITÉ ============
            "monuments de ouidah": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": ""},
            "temple des pythons": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Temple des Pythons"},
            "fort portugais": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Fort Portugais – Musée d’Histoire"},
            "forêt sacrée de kpassè": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Forêt Sacrée de Kpassè"},
            "kpassè": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Forêt Sacrée de Kpassè"},
            "basilique": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Basilique de l’Immaculée Conception"},
            "basilique de ouidah": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Basilique de l’Immaculée Conception"},
            "maison du brésil": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "La Maison du Brésil - Casa do Brasil"},
            "casa do brasil": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "La Maison du Brésil - Casa do Brasil"},
            "fondation zinsou": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Musée de la Fondation Zinsou (Ouidah)"},
            "musée zinsou": {"pole": "Ouidah", "category": "Monuments et Spiritualité", "subcategory": "Musée de la Fondation Zinsou (Ouidah)"},
            
            # ============ GANVIÉ - PRÉSENTATION ============
            "ganvié": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            "ganvie": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            "cité lacustre": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            "cité de ganvié": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            "lac nokoué": {"pole": "Ganvié", "category": "Présentation de Ganvié", "subcategory": ""},
            
            # ============ GANVIÉ - MODE DE VIE ============
            "marché flottant": {"pole": "Ganvié", "category": "Mode de vie des habitants de Ganvié et marché flottant", "subcategory": ""},
            "marché de ganvié": {"pole": "Ganvié", "category": "Mode de vie des habitants de Ganvié et marché flottant", "subcategory": ""},
            "habitants de ganvié": {"pole": "Ganvié", "category": "Mode de vie des habitants de Ganvié et marché flottant", "subcategory": ""},
            "maisons sur pilotis": {"pole": "Ganvié", "category": "Mode de vie des habitants de Ganvié et marché flottant", "subcategory": ""},
            
            # ============ GANVIÉ - LÉGENDE ============
            "agbogdobé": {"pole": "Ganvié", "category": "Légende du roi Agbogdobé", "subcategory": ""},
            "roi agbogdobé": {"pole": "Ganvié", "category": "Légende du roi Agbogdobé", "subcategory": ""},
            "légende de ganvié": {"pole": "Ganvié", "category": "Légende du roi Agbogdobé", "subcategory": ""},
            
            # ============ PORTO-NOVO - PRÉSENTATION ============
            "porto-novo": {"pole": "Porto Novo", "category": "Présentation de Porto-Novo", "subcategory": ""},
            "porto novo": {"pole": "Porto Novo", "category": "Présentation de Porto-Novo", "subcategory": ""},
            "portonovo": {"pole": "Porto Novo", "category": "Présentation de Porto-Novo", "subcategory": ""},
            "adjacé": {"pole": "Porto Novo", "category": "Présentation de Porto-Novo", "subcategory": ""},
            "hogbonou": {"pole": "Porto Novo", "category": "Présentation de Porto-Novo", "subcategory": ""},
            
            # ============ PORTO-NOVO - ROIS ============
            "toffa": {"pole": "Porto Novo", "category": "Rois de Porto-Novo", "subcategory": "Toffa_Ier.docx"},
            "roi toffa": {"pole": "Porto Novo", "category": "Rois de Porto-Novo", "subcategory": "Toffa_Ier.docx"},
            "toffa 1er": {"pole": "Porto Novo", "category": "Rois de Porto-Novo", "subcategory": "Toffa_Ier.docx"},
            
            # ============ PORTO-NOVO - MONUMENTS ET MUSÉES ============
            "monuments de porto-novo": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": ""},
            "musée honmè": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Honmè"},
            "honmè": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Honmè"},
            "musée da silva": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Da Silva"},
            "da silva": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée Da Silva"},
            "grande mosquée": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Grande Mosquée afro-brésilienne"},
            "mosquée afro-brésilienne": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Grande Mosquée afro-brésilienne"},
            "jardin place bayol": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Jardin-Place Bayol"},
            "place bayol": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Jardin-Place Bayol"},
            "musée ethnographique": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée ethnographique Alexandre Sènou Adandé"},
            "musée alexandre sènou adandé": {"pole": "Porto Novo", "category": "Monuments et Musées", "subcategory": "Musée ethnographique Alexandre Sènou Adandé"},
        }
        print("Agent conversationnel prêt\n")
    
    # =========================================================================
    # DÉTECTION D'INTENTION
    # =========================================================================
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte en enlevant ponctuation et accents superflus"""
        text = text.lower().strip()
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
            'ciao', 'adieu', 'salut', 'à plus tard'
        ]
        
        query_lower = query.lower().strip()
        
        for farewell in farewells:
            if farewell in query_lower:
                return True
        
        return False
    
    def _is_small_talk(self, query: str) -> bool:
        """Détecte les conversations générales (small talk)"""
        query_normalized = self._normalize_text(query)

        # ============ MOTS-CLÉS PATRIMONIAUX (À PRIORISER) ============
        heritage_keywords = [
            # Pôles principaux
            'abomey', 'ouidah', 'ganvié', 'ganvie', 'porto', 'dahomey',
            
            # Rois
            'roi', 'rois', 'béhanzin', 'behanzin', 'ghézo', 'ghezo', 'guézo',
            'glèlè', 'glele', 'agadja', 'houégbadja', 'houegbadja', 'akaba',
            'toffa', 'agonglo', 'kpengla', 'tegbessou', 'adandozan', 'agoli',
            
            # Amazones
            'amazones', 'mino', 'agodjié', 'agojié', 'guerrières',
            
            # Lieux Abomey
            'palais', 'palais royaux', 'musée', 'place', 'goho',
            
            # Lieux Ouidah
            'esclave', 'esclaves', 'route', 'porte', 'non-retour', 'non retour',
            'arbre', 'oubli', 'retour', 'cases', 'zomaï', 'zoungbodji',
            'fosse', 'commune', 'chacha', 'enchères',
            
            # Monuments Ouidah
            'temple', 'pythons', 'fort', 'portugais', 'forêt', 'kpassè',
            'basilique', 'immaculée', 'maison', 'brésil', 'casa', 'brasil',
            'fondation', 'zinsou', 'statues', 'sculptures',
            
            # Ganvié
            'cité', 'lacustre', 'lac', 'nokoué', 'marché', 'flottant',
            'habitants', 'maisons', 'pilotis', 'agbogdobé', 'légende',
            
            # Porto-Novo
            'honmè', 'da silva', 'mosquée', 'afro-brésilienne', 'jardin',
            'bayol', 'ethnographique', 'alexandre', 'sènou', 'adandé',
            
            # Mots génériques patrimoine
            'histoire', 'culture', 'tradition', 'patrimoine', 'monument',
            'visiter', 'voir', 'découvrir', 'raconte', 'parle', 'explique'
        ]
        
        # ✅ PRIORITÉ 1 : Si mot-clé patrimonial détecté → PAS small talk
        for keyword in heritage_keywords:
            if keyword in query_normalized:
                return False
        
        # ============ PATTERNS DE VRAI SMALL TALK ============
        small_talk_patterns = [
            # Salutations / état
            'comment vas tu', 'comment vastu', 'comment allez vous', 'comment allezvous',
            'comment ca va', 'comment ça va', 'ça va', 'ca va',
            'how are you', 'howareyou', 'how do you do',
            
            # Présentation
            'qui es tu', 'qui estu', 'qui êtes vous', 'qui êtesvous',
            'what are you', 'whatareyou', 'who are you', 'whoareyou',
            
            # Capacités
            'tu fais quoi', 'vous faites quoi', 'what do you do',
            'tu peux faire quoi', 'tu sais faire quoi',
            
            # ❌ 'c est quoi', 'cest quoi', 'c\'est quoi' SUPPRIMÉS !
        ]
        
        # ✅ PRIORITÉ 2 : Vérifier les patterns de small talk
        for pattern in small_talk_patterns:
            pattern_normalized = pattern.replace(' ', '')
            if pattern_normalized in query_normalized.replace(' ', ''):
                return True
        
        return False
    
    def _is_off_topic(self, query: str) -> bool:
        """
        VERSION V3.6 FIXED : Détection hors-sujet RENFORCÉE
        
        NOUVEAU V3.6 :
        ✅ Détection mathématiques
        ✅ Détection personnalités contemporaines
        
        Détecte les sujets clairement hors patrimoine béninois
        """
        query_lower = query.lower()
        
        # D'abord vérifier si c'est patrimonial
        heritage_keywords = [
            'roi', 'rois', 'amazones', 'palais', 'abomey', 'ouidah', 'ganvié', 'ganvie',
            'porto novo', 'porto-novo', 'dahomey', 'esclave', 'monument', 'temple',
            'musée', 'museum', 'basilique', 'mosquée', 'tradition', 'culture',
            'histoire', 'heritage', 'patrimoine', 'légende', 'mythe', 'legend', 'myth',
            'vodun', 'vaudou', 'voodoo', 'python', 'divinité',
            'porte', 'arbre', 'place', 'goho', 'zomaï', 'kpassè',
            'immaculée', 'honmè', 'silva', 'bayol',
            'raconte', 'parle', 'explique', 'décris', 'présente',
            'tell', 'explain', 'describe', 'talk about',
            'récit', 'story', 'narration', 'histoire de',
            'visiter', 'visit', 'voir', 'see'
        ]
        
        for keyword in heritage_keywords:
            if keyword in query_lower:
                return False
        
        # ✅ NOUVEAU V3.6 : Détection mathématiques
        # Pattern : chiffres avec opérateurs mathématiques
        if re.search(r'\d+\s*[+\-*/x÷×]\s*\d+', query_lower):
            return True
        
        # Mots-clés mathématiques
        math_keywords = [
            'résous', 'solve', 'équation', 'equation', 'calcule', 'calculate',
            'résoudre', 'calculer', 'mathématiques', 'mathematics', 'math',
            'addition', 'soustraction', 'multiplication', 'division'
        ]
        
        for math_kw in math_keywords:
            if math_kw in query_lower:
                return True
        
        # ✅ NOUVEAU V3.6 : Personnalités contemporaines (hors patrimoine)
        modern_figures = [
            'trump', 'donald trump', 'biden', 'joe biden', 
            'macron', 'emmanuel macron', 'poutine', 'putin',
            'elon musk', 'musk', 'zuckerberg', 'mark zuckerberg',
            'obama', 'barack obama', 'clinton', 'bill clinton',
            'merkel', 'angela merkel', 'xi jinping', 'xi'
        ]
        
        for figure in modern_figures:
            if figure in query_lower:
                # Vérifier qu'il n'y a pas de contexte patrimonial
                heritage_context_keywords = [
                    'comme', 'comme le roi', 'à l\'instar de', 'comparé à',
                    'like', 'compared to', 'similar to'
                ]
                
                has_heritage_context = any(ctx in query_lower for ctx in heritage_context_keywords)
                
                if not has_heritage_context:
                    return True
        
        # Détection hors-sujet existante (V3.5)
        off_topic_keywords = [
            # Météo
            'météo', 'weather', 'pluie', 'soleil', 'température', 'climat',
            'temps qu\'il fait', 'prévisions', 'il pleut', 'il fait',
            'quel temps', 'temps fait', 'fait il',
            
            # Sport moderne
            'foot', 'football', 'soccer', 'match', 'basket', 'tennis',
            'champion', 'coupe', 'ligue', 'équipe', 'can', 'joueur',
            
            # Technologie
            'iphone', 'android', 'windows', 'ordinateur', 'computer', 'internet',
            'logiciel', 'wifi', 'smartphone', 'application mobile', 'software',
            
            # Médias sociaux
            'netflix', 'youtube', 'tiktok', 'instagram', 'facebook',
            'série tv', 'film récent', 'streaming',
            
            # Cuisine moderne
            'cuisine moderne', 'recette', 'restaurant', 'pizza', 'burger',
            'mcdo', 'kfc', 'fastfood', 'fast food',
            
            # Politique actuelle
            'élection', 'président actuel', 'talon', 'gouvernement actuel',
            'politique actuelle', 'current politics',
            
            # Finance
            'bitcoin', 'crypto', 'bourse', 'action', 'trading', 'investissement',
            
            # Santé moderne
            'covid', 'coronavirus', 'vaccin', 'médicament', 'docteur',
            
            # Travail/Études
            'emploi', 'job', 'travail', 'salaire', 'études', 'université actuelle'
        ]
        
        off_topic_count = 0
        for keyword in off_topic_keywords:
            if keyword in query_lower:
                off_topic_count += 1
        
        if off_topic_count > 0:
            return True
        
        # Détection spéciale pour "cuisine" seule (V3.5)
        if re.search(r'\bcuisine\b', query_lower):
            # Si "cuisine" sans contexte patrimonial = hors-sujet
            patrimoine_food_keywords = ['traditionnelle', 'ancestrale', 'historique', 'ancienne']
            has_heritage_context = any(kw in query_lower for kw in patrimoine_food_keywords)
            
            if not has_heritage_context:
                return True
        
        return False
    
    def _is_followup_response(self, query: str) -> bool:
        """
        VERSION V3.6 FIXED : Détection de suivi conversationnel RENFORCÉE
        
        ✅ Solution 2 : Renforcement strict
        
        Détecte UNIQUEMENT les vraies réponses de suivi sans nouvelle entité forte.
        
        Règle critique :
        Si une nouvelle entité patrimoniale est détectée, ce N'EST PAS un suivi.
        """
        query_lower = query.lower().strip()
        
        # ✅ NOUVEAU V3.6 : Vérifier d'abord si nouvelle entité forte
        detected_entity = self.detect_entity(query)
        
        if detected_entity:
            # Nouvelle entité forte détectée → PAS un suivi
            return False
        
        # Patterns strictement conversationnels (réponses courtes sans contenu)
        strict_followup_patterns = [
            'oui', 'ouais', 'ok', 'd\'accord', 'bien sûr',
            'continue', 'vas-y', 'vas y',
            'yes', 'yeah', 'sure', 'ok', 'alright',
            'go on', 'go ahead', 'continue'
        ]
        
        # Vérifier patterns stricts
        for pattern in strict_followup_patterns:
            if query_lower.startswith(pattern) or query_lower == pattern:
                return True
        
        # Patterns avec verbes d'action (ambigus)
        ambiguous_patterns = [
            'explique', 'dis-moi', 'dis moi', 'raconte', 'décris',
            'j\'aimerais savoir', 'dis m\'en plus', 'dis men plus',
            'tell me', 'explain', 'describe', 'talk about',
            'i\'d like to know', 'tell me more'
        ]
        
        for pattern in ambiguous_patterns:
            if pattern in query_lower:
                # Pattern trouvé mais pas d'entité → c'est un suivi
                # (car on a déjà vérifié l'absence d'entité au début)
                return True
        
        return False

    def _extract_context_from_history(self) -> Optional[Dict[str, Any]]:
        """Extrait l'entité de la dernière question pour le suivi"""
        if not self.conversation_history:
            return None
        
        for message in reversed(self.conversation_history):
            if message['role'] == 'user':
                last_query = message['content']
                detected_entity = self.detect_entity(last_query)
                
                if detected_entity and detected_entity.get('pole'):
                    return {
                        'entity': detected_entity,
                        'query': last_query
                    }
        
        return None
    
    def _detect_response_type(self, query: str) -> str:
        """Détermine le type de réponse attendu"""
        query_lower = query.lower()
        
        # Liste exhaustive des patterns de liste
        list_patterns = [
            # Français - Formulations complètes
            'qu\'est ce que je peux', 'que puis-je', 'que peut-on',
            'qu\'est-ce qu\'on peut', 'qu\'est-ce que je peux',
            'quels endroits', 'quels lieux', 'quels sites', 'quels monuments',
            'quelles choses', 'quelles attractions', 'quels éléments',
            'cite', 'cite-moi', 'cite moi', 'énumère', 'liste', 'liste-moi',
            'nomme', 'donne-moi', 'donne moi',
            'qu\'est-ce qu\'il y a', 'qu\'y a-t-il', 'qu\'y a t il',
            'quels sont les', 'quelles sont les', 'quels sont ses',
            'à visiter', 'à voir', 'à découvrir', 'à explorer',
            'je peux visiter', 'on peut visiter', 'tu peux visiter',
            'je peux voir', 'on peut voir', 'tu peux voir',
            'visiter à', 'voir à', 'découvrir à', 'explorer',
            'les principaux', 'les principaux sites', 'les principaux monuments',
            'les différents', 'les différents sites', 'les différents monuments',
            'tous les', 'toutes les', 'l\'ensemble des',
            
            # Français - Patterns partiels (dans la phrase)
            'peux visiter', 'peut visiter', 'peux voir', 'peut voir',
            'visiter dans', 'voir dans', 'visiter en', 'voir en',
            'endroits à', 'lieux à', 'sites à', 'monuments à',
            'choses à', 'attractions à', 'éléments à',
            'que faire', 'quoi faire', 'quoi visiter', 'où aller',
            
            # Anglais
            'what can i', 'what can we', 'what can you',
            'what can one', 'what can people',
            'which places', 'which sites', 'which monuments',
            'which things', 'which attractions', 'which elements',
            'list', 'list of', 'give me', 'tell me',
            'what are the', 'what are its', 'what is there',
            'to visit', 'to see', 'to discover', 'to explore',
            'i can visit', 'we can visit', 'you can visit',
            'i can see', 'we can see', 'you can see',
            'visit in', 'see in', 'visit at', 'see at',
            'the main', 'the main sites', 'the main monuments',
            'the different', 'the different sites', 'different monuments',
            'all the', 'all of the',
            
            # Anglais - Patterns partiels
            'can visit', 'can see', 'to visit in', 'to see in',
            'places to', 'sites to', 'monuments to',
            'things to', 'attractions to', 'elements to',
            'what to do', 'where to go', 'what to visit'
        ]
        
        # Vérifier chaque pattern
        for pattern in list_patterns:
            if pattern in query_lower:
                return 'list'
        
        # Détection par mot-clé + contexte
        query_words = query_lower.split()
        
        # Si la question contient "quels" + nom au pluriel
        if 'quels' in query_words or 'quelles' in query_words:
            for i, word in enumerate(query_words):
                if word in ['quels', 'quelles'] and i + 1 < len(query_words):
                    next_word = query_words[i + 1]
                    if any(plural in next_word for plural in [
                        'sites', 'monuments', 'endroits', 'lieux',
                        'choses', 'attractions', 'éléments', 'rois',
                        'amazones', 'palais', 'musées', 'temples'
                    ]):
                        return 'list'
        
        # Questions qui commencent par "Quels/Quelles sont..."
        if query_lower.startswith(('quels sont', 'quelles sont', 'what are', 'which are')):
            return 'list'
        
        # Narrative
        narrative_keywords = [
            'raconte', 'raconte moi', 'raconte-moi', 'parle moi', 'parle-moi',
            'explique moi', 'explique-moi', 'décris', 'décris moi',
            'histoire de', 'récit de', 'légende de', 'conte',
            'tell me about', 'tell the story', 'describe', 'explain',
            'en détail', 'in detail', 'plus de détails', 'more details'
        ]
        
        for keyword in narrative_keywords:
            if keyword in query_lower:
                return 'narrative'
        
        # Short answer
        short_answer_keywords = [
            'qui est', 'qui était', 'c\'est qui', 'c\'est quoi', 'qu\'est-ce que',
            'quel est', 'quelle est', 'quand', 'où', 'où se trouve',
            'combien', 'est-ce que', 'y a-t-il',
            'who is', 'who was', 'what is', 'what was', 'when', 'where',
            'how much', 'is there', 'are there'
        ]
        
        for keyword in short_answer_keywords:
            if keyword in query_lower:
                return 'short_answer'
        
        # Fallback
        query_words = query_lower.split()
        
        if len(query_words) <= 5:
            return 'short_answer'
        
        if len(query_words) <= 10:
            return 'narrative'
        
        return 'narrative'
    
    def _needs_rag(self, query: str) -> bool:
        """Détermine si la question nécessite le RAG"""
        query_normalized = self._normalize_text(query)
        query_words = query_normalized.split()
        
        # Vérifier les mots-clés patrimoniaux
        heritage_keywords = [
            'roi', 'rois', 'ghézo', 'ghezo', 'guézo', 'béhanzin', 'behanzin', 
            'glèlè', 'glele', 'agadja', 'houégbadja', 'houegbadja', 'akaba', 
            'toffa', 'agonglo', 'kpengla', 'tegbessou', 'adandozan', 'agoli',
            'king', 'kings', 'souverain', 'monarque',
            'amazones', 'mino', 'agodjié', 'agojié', 'guerrières', 'amazons', 'warriors',
            'palais', 'abomey', 'ouidah', 'ganvié', 'ganvie',
            'porto novo', 'portonovo', 'porto-novo', 'dahomey',
            'musée', 'museum', 'temple', 'basilique', 'mosquée',
            'monument', 'site', 'palace', 'cité', 'ville', 'fort',
            'route', 'esclaves', 'slaves', 'traite', 'esclavage',
            'histoire', 'history', 'culture', 'tradition', 'coutume',
            'heritage', 'patrimoine', 'légende', 'mythe', 'legend', 'myth',
            'vodun', 'vaudou', 'voodoo', 'python', 'divinité',
            'porte', 'arbre', 'place', 'goho', 'zomaï', 'kpassè',
            'immaculée', 'honmè', 'silva', 'bayol',
            'raconte', 'parle', 'explique', 'décris', 'présente',
            'tell', 'explain', 'describe', 'talk about',
            'récit', 'story', 'narration', 'histoire de',
            'visiter', 'visit', 'voir', 'see'
        ]
        
        for keyword in heritage_keywords:
            if keyword in query_normalized:
                return True
        
        if len(query_words) <= 2:
            return False
        
        action_verbs = [
            'raconte', 'parle', 'explique', 'décris', 'présente',
            'tell', 'explain', 'describe'
        ]
        if any(verb in query_normalized for verb in action_verbs):
            return True
        
        if len(query_words) <= 4:
            return False
        
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
        
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
    
    def get_formatted_history(self, last_n: int = 3) -> str:
        """Retourne l'historique formaté pour le prompt"""
        if not self.conversation_history:
            return ""
        
        history_text = "HISTORIQUE DE LA CONVERSATION :\n"
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
        print("Conversation réinitialisée")
    
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
    
    def filter_relevant_images(
        self,
        results: List[Dict],
        query: str,
        detected_entity: Optional[Dict]
    ) -> List[str]:
        """Filtre les images pour ne garder que celles pertinentes"""
        if not results:
            return []
        
        target_pole = detected_entity.get('pole') if detected_entity else None
        target_category = detected_entity.get('category') if detected_entity else None
        target_subcategory = detected_entity.get('subcategory') if detected_entity else None
        
        relevant_images = []
        seen = set()
        
        for i, chunk in enumerate(results[:5]):
            chunk_pole = chunk.get('pole', '')
            chunk_category = chunk.get('category', '')
            chunk_subcategory = chunk.get('subcategory', '')
            
            relevance_score = 0
            
            if target_subcategory and chunk_subcategory == target_subcategory:
                relevance_score = 3
            elif target_category and chunk_category == target_category:
                relevance_score = 2
            elif target_pole and chunk_pole == target_pole:
                relevance_score = 1
            else:
                continue
            
            if relevance_score > 0:
                for img in chunk.get('images', []):
                    if img and img not in seen:
                        relevant_images.append({
                            'url': img,
                            'score': relevance_score,
                            'rank': i
                        })
                        seen.add(img)
        
        relevant_images.sort(key=lambda x: (-x['score'], x['rank']))
        
        return [img['url'] for img in relevant_images[:6]]
    
    def _filter_images_by_generated_text(
        self,
        generated_text: str,
        all_images: List[str],
        results: List[Dict]
    ) -> List[str]:
        """
        Filtre les images pour ne garder que celles des entités 
        mentionnées dans le texte généré par Gemini
        """
        if not all_images or not results:
            return []
        
        generated_lower = generated_text.lower()
        
        # Mapping image -> métadonnées du chunk
        image_metadata = {}
        for chunk in results:
            for img in chunk.get('images', []):
                if img not in image_metadata:
                    image_metadata[img] = {
                        'subcategory': chunk.get('subcategory', ''),
                        'category': chunk.get('category', ''),
                        'pole': chunk.get('pole', '')
                    }
        
        # Entités à rechercher
        entities_to_check = []
        
        for entity_name, entity_data in self.entity_mapping.items():
            if entity_name in generated_lower:
                entities_to_check.append({
                    'name': entity_name,
                    'subcategory': entity_data.get('subcategory', ''),
                    'category': entity_data.get('category', ''),
                    'pole': entity_data.get('pole', '')
                })
        
        # Si aucune entité spécifique détectée, vérifier les catégories générales
        if not entities_to_check:
            if 'ouidah' in generated_lower:
                entities_to_check.append({'pole': 'Ouidah', 'category': '', 'subcategory': ''})
            if 'abomey' in generated_lower:
                entities_to_check.append({'pole': 'Abomey', 'category': '', 'subcategory': ''})
            if 'ganvié' in generated_lower or 'ganvie' in generated_lower:
                entities_to_check.append({'pole': 'Ganvié', 'category': '', 'subcategory': ''})
            if 'porto' in generated_lower:
                entities_to_check.append({'pole': 'Porto Novo', 'category': '', 'subcategory': ''})
        
        # Filtrer les images
        relevant_images = []
        seen = set()
        
        for img in all_images:
            if img in seen:
                continue
                
            img_meta = image_metadata.get(img, {})
            
            # Vérifier si l'image correspond à une entité mentionnée
            for entity in entities_to_check:
                match = False
                
                if entity.get('subcategory') and img_meta.get('subcategory') == entity['subcategory']:
                    match = True
                elif entity.get('category') and img_meta.get('category') == entity['category']:
                    match = True
                elif entity.get('pole') and img_meta.get('pole') == entity['pole'] and not entity.get('category'):
                    match = True
                
                if match:
                    relevant_images.append(img)
                    seen.add(img)
                    break
        
        return relevant_images
    
    def _validate_rag_relevance(
        self,
        query: str,
        results: List[Dict],
        detected_entity: Optional[Dict],
        filtered_images: List[str]
    ) -> bool:
        """
        VERSION V3.4 : Valide si les résultats RAG sont vraiment pertinents
        """
        
        # Critère 1 : Si entité claire détectée avec subcategory
        if detected_entity and detected_entity.get('subcategory'):
            return True
        
        # Critère 2 : Si images pertinentes trouvées
        if filtered_images and len(filtered_images) > 0:
            return True
        
        # Critère 3 : Vérifier mots-clés patrimoniaux
        heritage_keywords = [
            'roi', 'rois', 'amazones', 'palais', 'abomey', 'ouidah',
            'ganvié', 'ganvie', 'porto', 'porto-novo', 'porto novo',
            'dahomey', 'temple', 'musée', 'museum', 'monument',
            'esclave', 'route', 'porte', 'fort', 'basilique',
            'mosquée', 'vodun', 'python', 'histoire', 'culture',
            'tradition', 'patrimoine', 'heritage', 'béhanzin',
            'ghézo', 'glèlè', 'houégbadja', 'agadja', 'toffa',
            'mino', 'agodjié', 'agojié', 'guerrières', 'warriors',
            'légende', 'mythe', 'récit', 'conte', 'story'
        ]
        
        query_lower = query.lower()
        has_heritage_keyword = any(kw in query_lower for kw in heritage_keywords)
        
        # Si pas de mot patrimonial -> vérifier scores
        if not has_heritage_keyword:
            if results:
                scores = [r.get('score', 0) for r in results]
                max_score = max(scores) if scores else 0
                avg_score = sum(scores) / len(scores) if scores else 0
                
                if max_score < 0.7 or avg_score < 0.5:
                    return False
            else:
                return False
        
        return True
    
    def retrieve_context(
        self,
        query: str,
        top_k: int = 10,
        verbose: bool = True
    ) -> Optional[Dict]:
        """Récupère le contexte pertinent via RAG"""
        
        filter_dict, detected = self.build_smart_filter(query)
        
        if verbose and detected:
            print(f"Entité détectée:")
            if detected.get('subcategory'):
                print(f"   {detected['subcategory']}")
            if detected.get('category'):
                print(f"   {detected['category']}")
            if detected.get('pole'):
                print(f"   {detected['pole']}")
        
        query_embedding = self.embeddings.embed_query(query)
        
        search_params = {
            'vector': query_embedding,
            'top_k': top_k,
            'include_metadata': True
        }
        
        if filter_dict:
            search_params['filter'] = filter_dict
        
        pinecone_results = self.index.query(**search_params)
        
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
            print(f"\nPipeline RAG:")
            print(f"   Pinecone: {len(results)} chunks")
        
        results = self.rerank_results(results, query)
        if verbose:
            print(f"   Reranking: {len(results)} chunks")
        
        results = self.deduplicate_chunks(results)
        if verbose:
            print(f"   Déduplication: {len(results)} chunks")
        
        filtered_images = self.filter_relevant_images(results, query, detected)
        if verbose:
            print(f"   Images filtrées: {len(filtered_images)} images pertinentes")
        
        llm_context = self.prepare_llm_context(results, query)
        
        llm_context['images'] = filtered_images
        llm_context['detected_entity'] = detected
        
        return llm_context
    
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
        
        all_sources = []
        seen_sources = set()
        
        for chunk in selected:
            for source in chunk['sources']:
                source_normalized = source.lower().strip()
                if source_normalized not in seen_sources:
                    all_sources.append(source)
                    seen_sources.add(source_normalized)
        
        unique_sources = all_sources[:5]
        
        return {
            'context': '\n'.join(context_parts),
            'images': [],
            'sources': unique_sources,
            'chunks_used': len(selected),
            'results': selected
        }
    
    # =========================================================================
    # GÉNÉRATION
    # =========================================================================
    
    def build_conversational_prompt(
        self,
        query: str,
        context: Optional[str],
        language: str = "fr",
        response_type: str = "narrative"
    ) -> str:
        """Construit le prompt avec instructions adaptées au type de réponse"""
        
        system_prompt = AGENT_SYSTEM_PROMPT_FR if language == "fr" else AGENT_SYSTEM_PROMPT_EN
        
        history_text = self.get_formatted_history(last_n=3)
        
        if context and context.strip():
            context_text = f"""
CONTEXTE DOCUMENTAIRE DISPONIBLE :
{context}

Utilise ce contexte pour enrichir ta réponse avec des faits précis.
"""
        else:
            context_text = """
Aucun contexte documentaire spécifique n'est disponible pour cette question.
Tu peux :
- Répondre avec tes connaissances générales sur le Bénin si pertinent
- Demander une clarification si la question est trop vague
- Rediriger vers un sujet connexe du patrimoine béninois

IMPORTANT : Si la question est hors de ton domaine d'expertise (météo, sport, cuisine moderne, etc.),
redirige BRIÈVEMENT (maximum 2 phrases) vers le patrimoine béninois.
"""
        
        if language == "fr":
            if response_type == "short_answer":
                response_instruction = """
INSTRUCTIONS SPÉCIALES - RÉPONSE COURTE :
Cette question demande une réponse FACTUELLE et CONCISE.

Format attendu :
1. Réponse directe en 1-2 phrases maximum
2. Information essentielle uniquement
3. Proposition d'en savoir plus avec enthousiasme

À ÉVITER :
- Récits longs
- Détails exhaustifs
- Paragraphes multiples

EXEMPLE PARFAIT :
Question : "Qui est le 5e roi d'Abomey ?"
Réponse : "Le 5e roi d'Abomey était Agadja, qui régna de 1708 à 1732 et conquit le royaume d'Allada. Veux-tu que je te raconte son histoire fascinante ?"

GARDE cette réponse COURTE et propose d'approfondir !
"""
            
            elif response_type == "list":
                response_instruction = """
INSTRUCTIONS SPÉCIALES - FORMAT LISTE :
Cette question demande une LISTE ou ÉNUMÉRATION.

Format attendu :
1. Introduction courte (1 phrase)
2. Liste claire avec tirets ou numéros
3. 1-2 phrases par élément
4. Conclusion engageante

EXEMPLE :
Question : "Quels sont les rois les plus célèbres d'Abomey ?"
Réponse : "Voici les rois les plus emblématiques du Dahomey :

- Ghézo (1818-1858) : Développa le commerce et renforça l'armée avec les Amazones
- Béhanzin (1889-1894) : Résista héroïquement à la colonisation française
- Glèlè (1858-1889) : Consolida le royaume et poursuivit l'expansion

Veux-tu en savoir plus sur l'un d'eux ?"
"""
            
            else:
                response_instruction = """
INSTRUCTIONS SPÉCIALES - RÉCIT NARRATIF :
Cette question demande un RÉCIT COMPLET et CAPTIVANT.

Format attendu :
- 3-4 paragraphes fluides
- Storytelling engageant
- Contexte historique
- Anecdotes et détails vivants
- Ton chaleureux de conteuse

STYLE :
Raconte comme si tu faisais revivre l'histoire, pas comme une encyclopédie.
Utilise des transitions naturelles entre les idées.
"""
        
        else:
            if response_type == "short_answer":
                response_instruction = """
SPECIAL INSTRUCTIONS - SHORT ANSWER:
This question requires a FACTUAL and CONCISE response.

Expected format:
1. Direct answer in 1-2 sentences maximum
2. Essential information only
3. Enthusiastic offer to know more

AVOID:
- Long narratives
- Exhaustive details
- Multiple paragraphs

PERFECT EXAMPLE:
Question: "Who is the 5th king of Abomey?"
Answer: "The 5th king of Abomey was Agadja, who reigned from 1708 to 1732 and conquered the Allada kingdom. Would you like me to tell you his fascinating story?"

KEEP this answer SHORT and offer to deepen!
"""
            
            elif response_type == "list":
                response_instruction = """
SPECIAL INSTRUCTIONS - LIST FORMAT:
This question requires a LIST or ENUMERATION.

Expected format:
1. Short introduction (1 sentence)
2. Clear list with bullets or numbers
3. 1-2 sentences per item
4. Engaging conclusion

EXAMPLE:
Question: "What are the most famous kings of Abomey?"
Answer: "Here are the most emblematic kings of Dahomey:

- Ghezo (1818-1858): Developed trade and strengthened the army with the Amazons
- Behanzin (1889-1894): Heroically resisted French colonization
- Glèlè (1858-1889): Consolidated the kingdom and continued expansion

Would you like to know more about one of them?"
"""
            
            else:
                response_instruction = """
SPECIAL INSTRUCTIONS - NARRATIVE:
This question requires a COMPLETE and CAPTIVATING NARRATIVE.

Expected format:
- 3-4 fluid paragraphs
- Engaging storytelling
- Historical context
- Living anecdotes and details
- Warm storyteller tone

STYLE:
Tell as if bringing history back to life, not like an encyclopedia.
Use natural transitions between ideas.
"""
        
        if language == "fr":
            prompt = f"""
{system_prompt}

---

{history_text}

{context_text}

{response_instruction}

QUESTION ACTUELLE DE L'UTILISATEUR :
{query}

---

TA RÉPONSE (en français, adaptée au type de question) :
"""
        else:
            prompt = f"""
{system_prompt}

---

{history_text}

{context_text}

{response_instruction}

USER'S CURRENT QUESTION:
{query}

---

YOUR RESPONSE (in English, adapted to question type):
"""
        
        return prompt
    
    def generate_response(
        self,
        query: str,
        language: str = "fr",
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Pipeline complet - VERSION V3.6 FIXED
        
        ✅ CORRECTIONS V3.6 :
        1. Détection entité AVANT détection suivi (Solution 1 CRITIQUE)
        2. _is_followup_response() renforcée (Solution 2 IMPORTANT)
        3. Détection hors-sujet améliorée (Solution 3 SECONDAIRE)
        
        ORDRE CORRECT :
        1. Détections rapides (greeting, thanks, farewell, small_talk)
        2. Détection hors-sujet RENFORCÉE AVANT RAG
        3. ✅ NOUVEAU : Détection ENTITÉ en premier
        4. ✅ NOUVEAU : Puis détection suivi (avec vérification entité)
        5. Déterminer type de réponse
        6. RAG si nécessaire
        7. VALIDATION DE PERTINENCE RAG
        8. Génération avec Gemini
        9. Filtrage POST-GÉNÉRATION des images
        10. Application des règles selon le type de réponse
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"QUESTION: {query}")
            print(f"{'='*80}")
        
        self.add_to_history("user", query)
        
        # PHASE 1 : DÉTECTIONS RAPIDES
        
        if self._is_greeting(query):
            if verbose:
                print("Détection: Salutation")
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
                'response_type': 'simple',
                'language': language
            }
        
        if self._is_thanks(query):
            if verbose:
                print("Détection: Remerciement")
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
                'response_type': 'simple',
                'language': language
            }
        
        if self._is_farewell(query):
            if verbose:
                print("Détection: Au revoir")
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
                'response_type': 'simple',
                'language': language
            }
        
        if self._is_small_talk(query):
            if verbose:
                print("Détection: Small talk")
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
                'response_type': 'simple',
                'language': language
            }
        
        # PHASE 2 : DÉTECTION HORS-SUJET RENFORCÉE (V3.6)
        
        if self._is_off_topic(query):
            if verbose:
                print("Détection: Hors-sujet (RENFORCÉE V3.6)")
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
                'response_type': 'simple',
                'language': language
            }
        
        # ✅ PHASE 2.5 : DÉTECTION ENTITÉ EN PREMIER (SOLUTION 1 CRITIQUE)
        
        detected_entity_current = self.detect_entity(query)
        
        # ✅ PHASE 2.6 : DÉTECTION SUIVI (SOLUTION 2 - après vérification entité)
        
        is_followup = self._is_followup_response(query)
        context_from_history = None
        
        if is_followup:
            # C'est un suivi uniquement si PAS de nouvelle entité forte
            context_from_history = self._extract_context_from_history()
            
            if context_from_history and verbose:
                print(f"Réponse de suivi détectée")
                print(f"   Contexte récupéré: {context_from_history['query']}")
                print(f"   Entité: {context_from_history['entity']}")
        elif detected_entity_current and verbose:
            # Nouvelle entité détectée → pas un suivi
            print(f"Nouvelle entité détectée → Reset contexte conversationnel")
        
        # PHASE 3 : DÉTERMINER LE TYPE DE RÉPONSE
        
        if is_followup and context_from_history:
            response_type = 'narrative'
        else:
            response_type = self._detect_response_type(query)
        
        if verbose:
            print(f"Type de réponse: {response_type}")
        
        # PHASE 4 : DÉCISION RAG
        
        if is_followup and context_from_history:
            needs_rag = True
            if verbose:
                print(f"Décision RAG: OUI (suivi conversationnel)")
        else:
            needs_rag = self._needs_rag(query)
            if verbose:
                print(f"Décision RAG: {'OUI' if needs_rag else 'NON'}")
        
        # PHASE 5 : RETRIEVAL
        
        llm_context = None
        context_text = None
        all_candidate_images = []
        filtered_images = []
        sources = []
        
        if needs_rag:
            if is_followup and context_from_history:
                previous_query = context_from_history['query']
                llm_context = self.retrieve_context(previous_query, verbose=verbose)
            else:
                llm_context = self.retrieve_context(query, verbose=verbose)
            
            if llm_context:
                context_text = llm_context['context']
                all_candidate_images = llm_context.get('images', [])
                sources = llm_context.get('sources', [])
                
                if verbose:
                    print(f"   Contexte: {llm_context['chunks_used']} chunks")
                    print(f"   Images candidates: {len(all_candidate_images)} images")
                    print(f"   Sources: {len(sources)} sources")
                
                # PHASE 5.5 : VALIDATION DE PERTINENCE RAG
                is_relevant = self._validate_rag_relevance(
                    query=query,
                    results=llm_context.get('results', []),
                    detected_entity=llm_context.get('detected_entity'),
                    filtered_images=all_candidate_images
                )
                
                if not is_relevant:
                    if verbose:
                        print(f"   VALIDATION: RAG NON PERTINENT - Suppression contexte et sources")
                    context_text = None
                    sources = []
                    all_candidate_images = []
                
            else:
                if verbose:
                    print("   Aucun contexte trouvé dans la base")
        
        # PHASE 6 : GÉNÉRATION AVEC GEMINI
        
        if verbose:
            print(f"\nGénération avec Gemini ({response_type})...")
        
        try:
            prompt = self.build_conversational_prompt(
                query,
                context_text,
                language,
                response_type
            )
            
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
                print(f"Réponse générée ({len(generated_text)} caractères)")
            
            # PHASE 6.5 : FILTRAGE POST-GÉNÉRATION DES IMAGES
            
            if llm_context and all_candidate_images:
                filtered_images = self._filter_images_by_generated_text(
                    generated_text,
                    all_candidate_images,
                    llm_context.get('results', [])
                )
                
                if verbose:
                    print(f"   Images après filtrage textuel: {len(filtered_images)} images")
                
                if response_type == 'list':
                    filtered_images = []
                    if verbose:
                        print(f"   Type 'list' : aucune image")
                
                elif response_type == 'short_answer':
                    if re.search(r'\b(où|where|se trouve|located|location)\b', query.lower()):
                        filtered_images = filtered_images[:2]
                        if verbose:
                            print(f"   Type 'short_answer' (localisation) : {len(filtered_images)} images")
                    else:
                        filtered_images = []
                        if verbose:
                            print(f"   Type 'short_answer' : aucune image")
                
                elif response_type == 'narrative':
                    filtered_images = filtered_images[:6]
                    if verbose:
                        print(f"   Type 'narrative' : {len(filtered_images)} images")
            
            self.add_to_history("assistant", generated_text)
            
            result = {
                'success': True,
                'query': query,
                'response': generated_text,
                'images': filtered_images,
                'sources': sources,
                'used_rag': needs_rag and llm_context is not None,
                'intent': 'heritage_question',
                'response_type': response_type,
                'language': language
            }
            
            if llm_context:
                result['chunks_used'] = llm_context['chunks_used']
                result['detected_entity'] = llm_context.get('detected_entity')
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"Erreur Gemini: {e}")
            
            return {
                'success': False,
                'error': f'Erreur lors de la génération: {str(e)}',
                'query': query,
                'response': "Désolée, j'ai rencontré un problème technique. Peux-tu reformuler ta question ?",
                'images': [],
                'sources': [],
                'used_rag': False,
                'intent': 'error',
                'response_type': 'simple',
                'language': language
            }
    
    def _generate_simple_response(self, query: str, intent: str, language: str) -> str:
        """
        VERSION V3.6 : Génère une réponse simple sans RAG pour les cas spéciaux
        
        ✅ NOUVEAU V3.6 : Redirections pour maths et personnalités
        """
        
        if language == "fr":
            if intent == "greeting":
                if len(self.conversation_history) <= 2:
                    return ("Bonjour ! Je suis ta guide culturelle virtuelle. "
                            "Je suis ravie de te faire découvrir les trésors du patrimoine béninois : "
                            "l'histoire des rois d'Abomey, les Amazones légendaires, les mystères d'Ouidah, "
                            "les cités lacustres de Ganvié et bien plus encore. "
                            "Que souhaites-tu découvrir aujourd'hui ?")
                else:
                    return "Bonjour ! Comment puis-je continuer à t'accompagner dans ta découverte du patrimoine béninois ?"
            
            elif intent == "thanks":
                return ("Avec grand plaisir ! C'est un honneur de partager la richesse culturelle "
                        "du Bénin avec toi. N'hésite pas si tu as d'autres questions sur notre "
                        "patrimoine !")
            
            elif intent == "farewell":
                return ("Au revoir ! J'espère que cette découverte du patrimoine béninois t'a plu. "
                        "Reviens quand tu veux pour en apprendre davantage. À très bientôt !")
            
            elif intent == "small_talk":
                query_lower = query.lower()
                
                if 'comment' in query_lower and ('va' in query_lower or 'allez' in query_lower):
                    return ("Je vais très bien, merci de demander ! En tant que gardienne des récits "
                            "béninois, je suis toujours enthousiaste à l'idée de partager notre riche "
                            "patrimoine. Et toi, es-tu prêt·e à découvrir une légende, un monument ou "
                            "un personnage historique ?")
                
                elif 'qui' in query_lower and ('es' in query_lower or 'êtes' in query_lower):
                    return ("Je suis ta guide culturelle virtuelle spécialisée dans le patrimoine "
                            "béninois. Mon rôle est de te faire découvrir l'histoire fascinante d'Abomey, "
                            "Ouidah, Ganvié et Porto-Novo à travers des récits vivants. Je peux te parler "
                            "des rois du Dahomey, des Amazones guerrières, des monuments sacrés, des "
                            "traditions... Que veux-tu savoir ?")
                
                elif 'fais' in query_lower or 'peux' in query_lower or 'sais' in query_lower:
                    return ("Je peux te raconter l'histoire fascinante du Bénin ! Les rois du Dahomey "
                            "et leurs exploits, les Amazones guerrières, la Route des Esclaves à Ouidah, "
                            "les cités lacustres de Ganvié, les musées de Porto-Novo... Je réponds à tes "
                            "questions avec des récits vivants, des images et des sources historiques. "
                            "Qu'est-ce qui t'intéresse ?")
                
                else:
                    return ("Je suis là pour partager avec toi les trésors du patrimoine béninois ! "
                            "N'hésite pas à me poser des questions sur nos rois, nos monuments, "
                            "nos traditions... Je suis à ton écoute !")
            
            elif intent == "off_topic":
                query_lower = query.lower()
                
                # ✅ NOUVEAU V3.6 : Redirections spécifiques
                
                # Mathématiques
                if re.search(r'\d+\s*[+\-*/x÷×]\s*\d+', query_lower) or \
                   any(math_kw in query_lower for math_kw in ['résous', 'solve', 'équation', 'calcule']):
                    return ("Les mathématiques ne sont pas mon domaine. Je me concentre sur l'histoire et le patrimoine béninois. Une question culturelle ?")
                
                # Personnalités modernes
                modern_figures = ['trump', 'biden', 'macron', 'poutine', 'musk', 'zuckerberg']
                if any(fig in query_lower for fig in modern_figures):
                    return ("Les personnalités contemporaines ne font pas partie de mon expertise. Je me concentre sur l'histoire béninoise. Intéressé par nos figures historiques comme les rois d'Abomey ?")
                
                # Redirections existantes (V3.5)
                if 'météo' in query_lower or 'weather' in query_lower or 'pluie' in query_lower or 'temps' in query_lower:
                    return ("Je suis spécialisée dans le patrimoine béninois, pas la météo. Puis-je te parler de nos sites historiques ?")
                
                elif 'sport' in query_lower or 'foot' in query_lower or 'match' in query_lower:
                    return ("Le sport moderne n'est pas mon domaine. Je peux par contre te parler des Amazones du Dahomey, des guerrières exceptionnelles !")
                
                elif any(tech in query_lower for tech in ['internet', 'ordinateur', 'téléphone', 'application', 'wifi', 'iphone', 'android']):
                    return ("La technologie moderne n'est pas mon expertise. Parlons plutôt de l'ingéniosité architecturale des palais d'Abomey ?")
                
                elif 'cuisine' in query_lower or 'recette' in query_lower or 'restaurant' in query_lower or 'pizza' in query_lower or 'burger' in query_lower:
                    return ("La cuisine moderne n'est pas mon domaine. Je me concentre sur le patrimoine historique et culturel du Bénin. Intéressé par notre histoire ?")
                
                elif any(pol in query_lower for pol in ['élection', 'politique actuelle', 'gouvernement']):
                    return ("La politique actuelle n'est pas mon domaine. Je peux te parler de l'histoire des rois du Dahomey et de leur organisation politique ?")
                
                else:
                    return ("Ce sujet sort de mon expertise. Je suis spécialisée dans le patrimoine béninois. Une question sur nos sites historiques ?")
        
        else:
            if intent == "greeting":
                if len(self.conversation_history) <= 2:
                    return ("Hello! I'm your virtual cultural guide. "
                            "I'm delighted to help you discover the treasures of Benin's heritage: "
                            "the history of Abomey's kings, the legendary Amazons, the mysteries of Ouidah, "
                            "the lake cities of Ganvié and much more. "
                            "What would you like to discover today?")
                else:
                    return "Hello! How can I continue to accompany you in your discovery of Benin's heritage?"
            
            elif intent == "thanks":
                return ("My great pleasure! It's an honor to share Benin's cultural richness "
                        "with you. Don't hesitate if you have other questions about our heritage!")
            
            elif intent == "farewell":
                return ("Goodbye! I hope you enjoyed discovering Benin's heritage. "
                        "Come back anytime to learn more. See you very soon!")
            
            elif intent == "small_talk":
                query_lower = query.lower()
                
                if 'how are you' in query_lower or 'how do you do' in query_lower:
                    return ("I'm doing great, thank you for asking! As a guardian of Beninese stories, "
                            "I'm always enthusiastic about sharing our rich heritage. And you, are you "
                            "ready to discover a legend, a monument or a historical figure?")
                
                elif 'who are you' in query_lower or 'what are you' in query_lower:
                    return ("I'm your virtual cultural guide specialized in Benin's heritage. "
                            "My role is to help you discover the fascinating history of Abomey, Ouidah, "
                            "Ganvié and Porto-Novo through living narratives. I can tell you about the "
                            "kings of Dahomey, the Amazon warriors, sacred monuments, traditions... "
                            "What would you like to know?")
                
                elif 'do you do' in query_lower or 'can you' in query_lower:
                    return ("I can tell you the fascinating history of Benin! The kings of Dahomey and "
                            "their exploits, the Amazon warriors, the Slave Route in Ouidah, the lake "
                            "cities of Ganvié, the museums of Porto-Novo... I answer your questions "
                            "with living narratives, images and historical sources. What interests you?")
                
                else:
                    return ("I'm here to share with you the treasures of Benin's heritage! Feel free "
                            "to ask me questions about our kings, monuments, traditions... I'm listening!")
            
            elif intent == "off_topic":
                query_lower = query.lower()
                
                # ✅ NOUVEAU V3.6 : English redirections
                
                # Mathematics
                if re.search(r'\d+\s*[+\-*/x÷×]\s*\d+', query_lower) or \
                   any(math_kw in query_lower for math_kw in ['solve', 'equation', 'calculate', 'math']):
                    return ("Mathematics isn't my domain. I focus on Benin's history and heritage. Any cultural questions?")
                
                # Modern figures
                modern_figures = ['trump', 'biden', 'macron', 'putin', 'musk', 'zuckerberg']
                if any(fig in query_lower for fig in modern_figures):
                    return ("Contemporary personalities aren't my expertise. I focus on Beninese history. Interested in our historical figures like the kings of Abomey?")
                
                # Existing redirections
                if 'weather' in query_lower or 'rain' in query_lower:
                    return ("I specialize in Benin's heritage, not weather. Can I tell you about our historical sites?")
                
                elif 'sport' in query_lower or 'football' in query_lower:
                    return ("Modern sports aren't my domain. I can tell you about the Dahomey Amazons, exceptional warriors!")
                
                elif 'cuisine' in query_lower or 'food' in query_lower or 'restaurant' in query_lower:
                    return ("Modern cuisine isn't my field. I focus on Benin's historical and cultural heritage. Interested in our history?")
                
                else:
                    return ("This topic is outside my expertise. I specialize in Benin's heritage. Any questions about our historical sites?")
        
        return "Je suis là pour t'aider !" if language == "fr" else "I'm here to help!"


# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

if __name__ == "__main__":
    
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    if not PINECONE_API_KEY or not GEMINI_API_KEY:
        print("Erreur: Variables d'environnement manquantes")
        print("Assurez-vous d'avoir PINECONE_API_KEY et GEMINI_API_KEY dans votre .env")
        exit(1)
    
    print("Initialisation de l'agent...\n")
    agent = BeninHeritageConversationalAgent(
        pinecone_api_key=PINECONE_API_KEY,
        gemini_api_key=GEMINI_API_KEY,
        index_name="benin-heritage"
    )
    
    print("\n" + "="*80)
    print("AGENT V3.6 FIXED - MODE CONVERSATIONNEL")
    print("="*80)
    print("\n✅ CORRECTIONS V3.6 :")
    print("  - Solution 1 : Détection entité AVANT détection suivi")
    print("  - Solution 2 : _is_followup_response() renforcée")
    print("  - Solution 3 : Détection hors-sujet améliorée (maths, personnalités)")
    print("\nCommandes spéciales:")
    print("  - 'reset' : Réinitialiser la conversation")
    print("  - 'quit' ou 'exit' : Quitter")
    print("\n" + "="*80 + "\n")
    
    while True:
        try:
            user_input = input("Vous : ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'quitter']:
                print("\nAu revoir ! À bientôt pour de nouvelles découvertes !\n")
                break
            
            if user_input.lower() == 'reset':
                agent.reset_conversation()
                print("\nConversation réinitialisée\n")
                continue
            
            result = agent.generate_response(
                query=user_input,
                language="fr",
                verbose=True
            )
            
            print(f"\nAgent : {result['response']}\n")
            
            if result.get('images'):
                print(f"Images ({len(result['images'])}):")
                for img in result['images'][:3]:
                    print(f"   - {img}")
                if len(result['images']) > 3:
                    print(f"   ... et {len(result['images']) - 3} autre(s)")
                print()
            
            if result.get('sources'):
                print(f"Sources ({len(result['sources'])}):")
                for src in result['sources'][:2]:
                    print(f"   - {src}")
                if len(result['sources']) > 2:
                    print(f"   ... et {len(result['sources']) - 2} autre(s)")
                print()
            
            print(f"Type: {result.get('response_type', 'N/A')} | "
                  f"RAG: {'OUI' if result.get('used_rag') else 'NON'} | "
                  f"Intent: {result.get('intent', 'N/A')}")
            print("\n" + "-"*80 + "\n")
            
        except KeyboardInterrupt:
            print("\n\nAu revoir !\n")
            break
        except Exception as e:
            print(f"\nErreur: {e}\n")
            continue