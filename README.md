# Agent Conversationnel Intelligent pour la Valorisation du Patrimoine Culturel Béninois

**Une application mobile intelligente qui valorise la richesse culturelle et historique du Bénin à travers une expérience narrative immersive.**


##  À propos du projet

Le projet est une application mobile intelligente conçue pour valoriser le patrimoine culturel et historique du Bénin. L'objectif n'est pas de fournir des informations pratiques comme un guide touristique classique, mais d'offrir une **rencontre vivante avec l'histoire**, racontée sous la forme d'un dialogue naturel entre l'utilisateur et un agent conversationnel multilingue et multimodal.

###  Pôles patrimoniaux couverts

L'application couvre quatre grands pôles patrimoniaux du Bénin :

- **Abomey** : Palais royaux, rois du Dahomey, Amazones
- **Ouidah** : Route des Esclaves, monuments historiques
- **Ganvié** : Cité lacustre, mode de vie traditionnel
- **Porto-Novo** : Mosquée afro-brésilienne, musées

###  Contexte académique

Ce projet a été développé dans le cadre d'un mémoire de Licence en Intelligence Artificielle à l'**IFRI (Institut de Formation et de Recherche en Informatique)**.

**Problématique** : Comment rendre le patrimoine béninois accessible, interactif et fiable à travers un agent conversationnel intelligent ?

**Objectifs** :
- Transmettre la mémoire culturelle aux jeunes générations
- Renforcer la visibilité du patrimoine béninois à l'échelle internationale
- Moderniser la médiation culturelle grâce à l'IA



##  Fonctionnalités

###  Agent Conversationnel 

- **Persona narrative** : Notre agent se présente comme une guide culturelle virtuelle chaleureuse
- **Conversation naturelle** : Questions libres en français et anglais
- **Réponses multimodales** :
  - Texte narratif et pédagogique
  - Images illustratives des sites et monuments
  - Audio TTS (Text-to-Speech) pour écouter les réponses
- **Mémoire conversationnelle** : Comprend les questions contextuelles
- **Sources vérifiées** : Réponses basées uniquement sur des documents validés

###  Application Mobile

- **Page d'accueil** : Découverte des 4 pôles patrimoniaux
- **Assistant IA** : Chat temps réel avec l'agent
  - Questions suggérées
  - Affichage des images en rapport avec la question posée
  - Lecture audio des réponses
  - Citations des sources
- **Pages détails** : Informations approfondies sur chaque site
- **Favoris** : Sauvegarde des sites et conversations préférés
- **Historique** : Consultation des échanges précédents

###  API REST

- `/chat` : Endpoint principal avec détection automatique de la langue
- `/history/{session_id}` : Récupération de l'historique conversationnel
- `/reset/{session_id}` : Réinitialisation de session
- `/health` : Vérification de l'état des services



##  Architecture

Le projet repose sur une architecture **RAG (Retrieval-Augmented Generation)** en 3 phases : préparation des données, pipeline conversationnel et exposition API.

### Phase 1 : Préparation et Indexation des Données

Le processus d'indexation commence avec le dossier Donnees_soutenance qui contient 43 documents Word (.docx) accompagnés de leurs images illustratives. Le script extraction_chunking_indexation.py parcourt cette arborescence organisée en 4 pôles patrimoniaux (Abomey, Ouidah, Ganvié, Porto-Novo). Pour chaque document, il extrait le contenu textuel ainsi que les métadonnées structurelles (pôle, catégorie, sous-catégorie, sources bibliographiques, images associées). Le texte extrait est ensuite découpé en segments cohérents appelés "chunks", de taille optimale pour la recherche sémantique. Chaque chunk est transformé en vecteur numérique de 384 dimensions grâce au modèle d'embeddings sentence-transformers/all-MiniLM-L6-v2. Enfin, ces vecteurs sont indexés dans Pinecone avec leurs métadonnées enrichies, créant ainsi une base vectorielle interrogeable. Ce processus génère trois outputs distincts : l'index Pinecone contenant environ 200 à 300 chunks vectorisés, un fichier JSON de sauvegarde locale dans le dossier chunks_backup/ pour traçabilité, et les images originales conservées dans leurs répertoires respectifs pour affichage ultérieur.

**Métadonnées enrichies** : Chaque chunk contient :
- `pole`, `category`, `subcategory` (navigation sémantique)
- `source_file`, `source_path` (traçabilité)
- `images[]` (chemins des illustrations)
- `sources[]` (références bibliographiques)
- `sections[]` (structure du document)
- `chunk_index`, `total_chunks` (pagination)

### Phase 2 : Pipeline RAG Conversationnel

L'interaction utilisateur démarre depuis l'application mobile React Native développée avec Expo, qui offre une interface de chat temps réel avec scroll automatique, affichage multimodal (texte, images, audio), gestion des favoris et historique des conversations, ainsi qu'un indicateur de connexion en temps réel. Lorsque l'utilisateur pose une question comme "Parle-moi du roi Ghézo", celle-ci est transmise via une requête HTTP POST à l'endpoint /chat de l'API REST développée avec FastAPI (fichier api_with_tts.py).
L'API expose plusieurs endpoints essentiels : l'endpoint principal /chat pour la conversation, /health pour le monitoring des services, /history/{session_id} pour récupérer l'historique conversationnel, /reset/{session_id} pour réinitialiser une session, /generate-audio pour la génération TTS manuelle, ainsi que le serving statique des fichiers audio et images via les routes /audio et /images. L'API gère également les sessions utilisateur avec persistance en mémoire, la détection automatique de langue (français/anglais), et active CORS pour permettre les requêtes depuis applications web et mobile.
La requête est ensuite traitée par l'agent conversationnel (fichier rag_conversational_agent_correction.py), qui représente l'aboutissement de trois étapes de développement successives. Le développement a commencé avec complete_rag.py, un premier pipeline RAG qui implémentait uniquement les fonctionnalités de retrieval (récupération) : recherche vectorielle dans Pinecone, filtrage intelligent par métadonnées (pôle, catégorie, sous-catégorie), reranking hybride combinant 60% de similarité vectorielle et 40% de correspondance de mots-clés, déduplication pour conserver maximum 2 chunks par document source, et préparation du contexte optimisé. Ce premier module n'incluait pas encore de génération de réponse par un LLM.
Dans une deuxième étape, le fichier rag_with_gemini.py a enrichi ce pipeline RAG en ajoutant la génération de réponses narratives via Google Gemini 2.5 Flash. Cette version combinait donc le retrieval complet de complete_rag.py avec la capacité de générer des réponses en langage naturel, appliquant déjà la persona de guide culturelle avec un ton narratif et pédagogique.
Enfin, la troisième et dernière étape a transformé ce générateur RAG simple en un véritable agent conversationnel intelligent dans rag_conversational_agent_correction.py. Cette transformation a ajouté plusieurs capacités essentielles : premièrement, l'analyse d'intention avec détection hiérarchique pour identifier s'il s'agit d'une salutation, d'un remerciement, d'une question patrimoniale, ou de small talk, en s'appuyant sur des marqueurs de mots-clés comme "roi", "lieu", "monument". Deuxièmement, l'extraction d'entités qui identifie automatiquement les rois, lieux et monuments mentionnés, puis les mappe vers les filtres Pinecone appropriés. Troisièmement, une mémoire conversationnelle qui conserve les 5 derniers échanges pour comprendre les questions de suivi contextuel (comme "Et ses Amazones ?" après avoir parlé de Ghézo). Quatrièmement, une prise de décision intelligente sur quand activer le pipeline RAG complet versus répondre directement pour les salutations ou questions simples.
L'enrichissement multimodal final extrait les images pertinentes depuis les métadonnées Pinecone, cite les sources bibliographiques pour traçabilité, et génère un fichier audio MP3 de la réponse via le service TTS (fichier tts_service.py) utilisant Edge-TTS de Microsoft. L'ensemble de ce pipeline s'appuie sur trois services externes essentiels : Pinecone pour la recherche vectorielle dans la base de connaissances, Google Gemini 2.5 Flash comme modèle de langage pour la génération de texte, et Edge-TTS pour la synthèse vocale en français et anglais.

### Composants clés

**1. Base documentaire** : 
- 43 documents Word (.docx) structurés hiérarchiquement
- 4 pôles : Abomey, Ouidah, Ganvié, Porto-Novo
- Images associées (JPG/PNG) dans chaque dossier
- Sources bibliographiques validées

**2. Indexation vectorielle** :
- Modèle d'embeddings : `sentence-transformers/all-MiniLM-L6-v2`
- Dimension : 384
- Métrique : Cosine similarity
- Stockage : Pinecone (cloud)
- Backup local : JSON dans `chunks_backup/`

**3. Pipeline RAG intelligent** :
- Détection d'intention multi-niveaux
- Filtrage sémantique par entités
- Reranking hybride (similarité + mots-clés)
- Déduplication pour éviter redondances
- Mémoire conversationnelle (5 derniers échanges)

**4. Génération multimodale** :
- LLM : Google Gemini 2.5 Flash
- Persona : Guide culturelle (FR/EN)
- Outputs : Texte + Images + Audio MP3
- TTS : Edge-TTS (voix française/anglaise)

**5. API REST complète** :
- Framework : FastAPI 
- Gestion sessions utilisateur
- Auto-détection langue via `langdetect`
- Serving statique (audio, images)
- Health checks des services



##  Technologies utilisées

### Backend
- **Python 3.12.2**
- **FastAPI** - Framework web asynchrone
- **Pinecone** - Base de données vectorielle
- **Google Generative AI** - LLM Gemini 2.5 Flash
- **HuggingFace Transformers** - Modèles d'embeddings
- **langdetect** - Détection automatique de langue
- **Edge-TTS** - Synthèse vocale
- **python-docx** - Extraction de documents Word

### Frontend
- **React Native** (Expo)
- **TypeScript**
- **Axios** - Client HTTP
- **expo-av** - Lecture audio
- **AsyncStorage** - Stockage local

### Infrastructure
- **Git/GitHub** - Gestion de version
- **Python Virtual Environment** - Isolation des dépendances


##  Prérequis

- **Python** 3.9 ou supérieur
- **Node.js** 18+ et npm/yarn
- **Expo CLI** (`npm install -g expo-cli`)
- **Compte Pinecone** (gratuit)
- **Clé API Google Gemini** (gratuit)
- **Git**



##  Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/AGBOSSOUNON-Mariane/new_version_of_soutenance_project.git

```

### 2. Configuration du Backend

```bash
cd backend

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration du Frontend

```bash
cd ../frontend
cd mon-projet-soutenance

# Installer les dépendances
npm install
# ou
yarn install
```



##  Configuration

### Backend - Variables d'environnement

Créez un fichier `.env` dans le dossier `backend/` :

```env
# Pinecone
PINECONE_API_KEY=votre_cle_pinecone
INDEX_NAME=benin-heritage

# Google Gemini
GEMINI_API_KEY=votre_cle_gemini

# Chemins
BASE_PATH=Donnees_soutenance

BASE_URL=http://localhost:8000
```

### Frontend - Configuration API

Modifiez le fichier `frontend/services/api.ts` :

```typescript
const API_BASE_URL = 'http://VOTRE_IP_LOCAL:8000';
```

> **Note** : Remplacez `VOTRE_IP_LOCAL` par l'adresse IP de votre machine (ex: `192.168.1.10`)



##  Utilisation

### Préparation : Indexation de la base documentaire

** Étape obligatoire avant la première utilisation**

Cette commande parcourt les 43 documents Word, les découpe en chunks et les indexe dans Pinecone avec métadonnées enrichies.

```bash
cd backend
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
python extraction_chunking_indexation.py
```

**Sortie attendue** :
```
 Scanning Donnees_soutenance/...
  Processing: Ghézo.docx
   ├─ Extracted 1847 chars
   ├─ Created 4 chunks
   ├─ Found 2 images
   └─ Indexed successfully
...
  Indexation terminée !
   Total documents : ...
   Total chunks    : ...
   Total images    : ...
```

**Fichiers générés** :
1. **Pinecone Index** : Vecteurs + métadonnées accessibles via API
2. **Backup JSON** : `chunks_backup/chunks_YYYYMMDD_HHMMSS.json`

**Exemple de chunk indexé** :
```json
{
  "text": "Ghézo, né prince Gakpe, régna sur Abomey pendant quarante ans, de 1818 à 1858. Il arrive au pouvoir après le renversement d'Adandozan...",
  "metadata": {
    "source_file": "Ghézo.docx",
    "source_path": "Donnees_soutenance\\Abomey\\Rois du Dahomey\\Guézo\\Ghézo.docx",
    "pole": "Abomey",
    "category": "Rois du Dahomey",
    "subcategory": "Guézo",
    "chunk_index": 0,
    "total_chunks": 4,
    "images": [
      "Donnees_soutenance\\Abomey\\Rois du Dahomey\\Guézo\\palais du roi Ghézo.jpg",
      "Donnees_soutenance\\Abomey\\Rois du Dahomey\\Guézo\\Symbole_de_Ghézo_roi_du_Dahomey.jpg"
    ],
    "sources": [
      "Wikipédia (FR) — Ghézo, https://fr.wikipedia.org/wiki/Gh%C3%A9zo",
      "Wikipédia (FR) — Rois d'Abomey, https://fr.wikipedia.org/wiki/Roi_d%27Abomey"
    ],
    "sections": [
      "Introduction",
      "Résumé",
      "Biographie complète",
      "Symboles, mythes et héritage"
    ]
  }
}
```

**Contenu Pinecone** (exemple) :
```
ID: Ghezo_docx_0
Vector: [0.123, -0.456, 0.789, ...] (384 dimensions)
Metadata:
  - pole: "Abomey"
  - category: "Rois du Dahomey"
  - subcategory: "Guézo"
  - images: "path1|path2|path3"
  - sources: "source1|source2"
  ...
```



### Lancer le Backend (API)

```bash
cd backend
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
python api_with_tts.py
```

L'API sera accessible sur `http://localhost:8000`

**Vérification** :
- Accéder à `http://localhost:8000/health` dans un navigateur
- Réponse attendue : `{"status": "healthy", "pinecone": {...}, ...}`

**Documentation interactive** :
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

### Lancer l'application mobile

```bash
cd frontend
npm start
# ou
expo start
```

Scannez le QR code avec **Expo Go** (iOS/Android) ou utilisez un émulateur.



##  Structure du projet

```
├── backend/
│   ├── Donnees_soutenance/           # Base documentaire 
│   │   ├── Abomey/
│   │   │   ├── Rois du Dahomey/
│   │   │   │   ├── Ghézo/
│   │   │   │   │   ├── Ghézo.docx
│   │   │   │   │   ├── palais du roi Ghézo.jpg
│   │   │   │   │   └── Symbole_de_Ghézo_roi_du_Dahomey.jpg
│   │   │   │   ├── Béhanzin/, Houégbadja/, ... (12 rois)
│   │   │   ├── Les Amazones du Dahomey/
│   │   │   ├── Lieux historiques et monuments d'Abomey/
│   │   │   └── Présentation d'Abomey/
│   │   ├── Ouidah/
│   │   │   ├── Route des Esclaves/
│   │   │   ├── Monuments et Spiritualité/
│   │   │   └── Présentation de Ouidah/
│   │   ├── Ganvié/
│   │   │   ├── Mode de vie et marché flottant/
│   │   │   └── Légende du roi Agbogdobé/
│   │   └── Porto Novo/
│   │       ├── Monuments et Musées/
│   │       ├── Rois de Porto-Novo/
│   │       └── Présentation de Porto-Novo/
│   │
│   ├── chunks_backup/                # Sauvegarde JSON des chunks
│   │   └── chunks_YYYYMMDD_HHMMSS.json
│   │
│   ├── audio_outputs/                # Fichiers audio TTS générés
│   │   └── response_*.mp3
│   │
│   ├── evaluation/                   # Scripts d'évaluation
│   │   ├── test_agent.py
│   │   └── metrics.py
│   │
│   ├── extraction_chunking_indexation.py  # Phase 1 : Indexation
│   ├── complete_rag.py                    # RAG core (retrieval)
│   ├── rag_with_gemini.py                 # RAG + génération Gemini
│   ├── rag_conversational_agent_correction.py  # Agent complet
│   ├── api_with_tts.py                    # API finale (main entry)
│   ├── tts_service.py                     # Service de synthèse vocale
│   │
│   ├── requirements.txt              # Dépendances Python
│   ├── .env                          # Variables d'environnement
│
├── frontend/
│   ├── app/
│   │   ├── (tabs)/
│   │   │   ├── _layout.tsx           # Navigation principale
│   │   │   ├── index.tsx             # Accueil (4 pôles)
│   │   │   ├── assistant.tsx         # Chat avec Adjä
│   │   │   ├── favoris.tsx           # Sites favoris
│   │   │   └── historique.tsx        # Historique conversations
│   │   └── details/                  # Pages détails sites
│   │       ├── abomey.tsx
│   │       ├── ouidah.tsx
│   │       ├── ganvie.tsx
│   │       └── portonovo.tsx
│   │
│   ├── components/
│   │   └── common/
│   │       └── Header.tsx            # Composant en-tête
│   │
│   ├── services/
│   │   ├── api.ts                    # Configuration Axios
│   │   └── ChatService.ts            # Service de chat
│   │
│   ├── constants/
│   │   └── Colors.ts                 # Palette de couleurs
│   │
│   ├── assets/                       # Images et ressources
│   ├── package.json                  # Dépendances Node.js
│   └── app.json                      # Configuration Expo
│
├── README.md                         # Documentation principale
├── CONTRIBUTING.md                   # Guide de contribution
├── LICENSE                           # Licence MIT
├── .gitignore                        # Fichiers à ignorer
├── CHANGELOG.md                      # Historique versions
└── SETUP.md                          # Guide d'installation détaillé
```

### Fichiers clés du backend

| Fichier | Description | Rôle |
|---------|-------------|------|
| `extraction_chunking_indexation.py` | Préparation données | Extrait, découpe et indexe les documents dans Pinecone |
| `complete_rag.py` | Pipeline RAG core | Recherche vectorielle + filtrage + reranking + déduplication |
| `rag_with_gemini.py` | RAG + génération | Complete RAG + appel Gemini pour génération narrative |
| `rag_conversational_agent_correction.py` | Agent complet | Détection intention + mémoire + génération contextuelle |
| `api_with_tts.py` | **API principale** | FastAPI + TTS + gestion sessions + serving static |
| `tts_service.py` | Synthèse vocale | Conversion texte→MP3 via Edge-TTS |



##  API Documentation

L'API REST expose plusieurs endpoints pour interagir avec l'agent.

### Endpoints principaux

#### 1. Conversation avec l'agent

**POST `/chat`**

Envoie un message à l'agent avec génération complète (texte + audio + images).

**Request Body** :
```json
{
  "generate_audio": true,
  "message": "Qui est le roi Ghézo ?",
  "session_id": "user-123-abc",
  "verbose": false
}
```

**Response** :
```json
{
  "response": "Ghézo, né prince Gakpe, régna sur Abomey pendant quarante ans, de 1818 à 1858...",
  "images": [
    "http://api_url/images/palais_du_roi_Ghezo.jpg",
    "http://api_url/images/Symbole_de_Ghezo_roi_du_Dahomey.jpg"
  ],
  "sources": [
    "Ghézo.docx",
    "Histoire_Abomey.docx"
  ],
  "audio_url": "http://api_url/audio/response_abc123.mp3",
  "session_id": "user-123-session",
  "detected_language": "fr"
}
```

**Fonctionnalités** :
-  Détection automatique langue (FR/EN via `langdetect`)
-  Génération audio TTS automatique
-  Extraction images des métadonnées Pinecone
-  Citations sources documentaires
-  Gestion mémoire conversationnelle



#### 2. Monitoring et santé

**GET `/health`**

Vérifie l'état de l'API et des services connectés.

**Response** :
```json
{
  "status": "healthy",
  "pinecone": {
    "connected": true,
    "index_name": "benin-heritage-index",
    "vector_count": 287
  },
  "gemini": {
    "connected": true,
    "model": "gemini-2.5-flash"
  },
  "tts": {
    "available": true,
    "engine": "edge-tts"
  },
  "timestamp": "2025-01-22T10:30:00Z"
}
```



#### 3. Gestion des sessions

**GET `/history/{session_id}`**

Récupère l'historique complet d'une session de conversation.

**Response** :
```json
{
  "session_id": "user-123-session",
  "history": [
    {
      "role": "user",
      "content": "Bonjour",
      "timestamp": "2025-01-22T10:15:00Z"
    },
    {
      "role": "assistant",
      "content": "Bonjour ! Je suis Adjä, votre guide culturelle...",
      "timestamp": "2025-01-22T10:15:01Z"
    }
  ],
  "total_exchanges": 5
}
```

**DELETE `/reset/{session_id}`**

Réinitialise une session de conversation (efface l'historique).

**Response** :
```json
{
  "message": "Session user-123-session reset successfully",
  "session_id": "user-123-session"
}
```


#### 4. Génération audio (endpoints avancés)

**POST `/generate-audio`**

Génère un fichier audio MP3 pour un texte donné.

**Request Body** :
```json
{
  "text": "Ceci est un test de génération audio",
  "language": "fr"
}
```

**Response** :
```json
{
  "audio_url": "http://api_url/audio/custom_xyz789.mp3",
  "duration_seconds": 5.2,
  "file_size_bytes": 83456
}
```

**POST `/generate-audio/stream`**

Streaming audio en temps réel (pour applications nécessitant lecture immédiate).

**Response** : Stream binaire MP3


#### 5. Maintenance

**POST `/audio/cleanup`**

Nettoie les fichiers audio temporaires de plus de 24h.

**Response** :
```json
{
  "deleted_files": 12,
  "freed_space_mb": 4.8
}
```



### Serving de fichiers statiques

L'API sert automatiquement les fichiers via :

- **`/audio/{filename}`** : Fichiers audio TTS générés
- **`/images/{path}`** : Images historiques des documents

Exemple :
```
GET http://api_url/audio/response_abc123.mp3
GET http://api_url/images/Abomey/Rois_du_Dahomey/Ghezo/palais_du_roi_Ghezo.jpg
```



### Gestion des erreurs

Toutes les erreurs retournent un format standardisé :

```json
{
  "detail": "Description de l'erreur",
  "error_code": "PINECONE_CONNECTION_ERROR",
  "timestamp": "2025-01-22T10:30:00Z"
}
```

**Codes HTTP** :
- `200` : Succès
- `400` : Requête invalide
- `404` : Ressource non trouvée
- `500` : Erreur serveur (Pinecone, Gemini, TTS)
- `503` : Service temporairement indisponible



### Authentification et CORS

- **Authentification** : Aucune (projet académique)
- **CORS** : Activé pour toutes origines (`allow_origins=["*"]`)
- **Rate limiting** : Non implémenté (à ajouter en production)



### Documentation interactive

Une fois l'API lancée, accédez à :

- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`

Ces interfaces permettent de tester tous les endpoints directement dans le navigateur.



##  Évaluation et Tests

Le projet inclut un dossier `evaluation/` pour tester et évaluer les performances de l'agent conversationnel.

### Tests disponibles

**Métriques évaluées** :
-  Pertinence des réponses (cohérence avec les sources)
-  Temps de réponse moyen
-  Qualité de la détection d'intention
-  Précision du filtrage par entités
  

### Scénarios de test

Le système teste plusieurs cas d'usage :

1. **Questions simples** : "Qui est le roi Ghézo ?"
2. **Questions contextuelles** : "Et ses Amazones ?" (après question sur Ghézo)
3. **Questions hors-sujet** : "Quelle est la météo ?"
4. **Conversations naturelles** : Salutations, remerciements



##  Détails Techniques Avancés

### Pipeline RAG : Fonctionnement détaillé

####  Détection d'intention hiérarchique

L'agent analyse chaque message selon une logique en cascade :

```python
# Ordre de priorité :
1. Salutations / remerciements → Réponse conversationnelle directe
2. Mots-clés patrimoniaux → Activation RAG
3. Questions courtes avec contexte → Utilisation historique
4. Hors-sujet → Redirection douce
```

**Marqueurs détectés** :
- Salutations : `bonjour`, `salut`, `hello`, `hi`, `bonsoir`
- Patrimoine : `roi`, `reine`, `amazone`, `palais`, `musée`, `monument`, `histoire`
- Lieux : `abomey`, `ouidah`, `ganvié`, `porto-novo`

####  Extraction et mapping d'entités

Le système repose sur une foction `entity_mapping` :

```python
 {
    "rois": {
        "ghezo": {"pole": "Abomey", "category": "Rois du Dahomey"},
        "behanzin": {"pole": "Abomey", "category": "Rois du Dahomey"},
        "toffa": {"pole": "Porto Novo", "category": "Rois de Porto-Novo"}
    },
    "lieux": {
        "palais royaux": {"pole": "Abomey", "category": "Lieux historiques"},
        "route des esclaves": {"pole": "Ouidah", "category": "Route des Esclaves"}
    }
}
```

**Utilité** : Permet un filtrage ultra-précis dans Pinecone via les métadonnées.

####  Reranking hybride

Combinaison de deux scores :

```python
score_final = 0.6 × similarité_vectorielle + 0.4 × score_mots_clés
```

- **Similarité vectorielle** : Distance cosinus entre embeddings
- **Score mots-clés** : Présence termes de la question dans le chunk

**Avantage** : Évite les réponses hors-contexte malgré similarité sémantique élevée.

####  Déduplication intelligente

Pour éviter les répétitions, le système :

1. Groupe les chunks par document source
2. Conserve maximum 2 chunks par document
3. Priorise les chunks avec score le plus élevé

**Résultat** : Contexte diversifié sans redondance narrative.

####  Mémoire conversationnelle

L'agent conserve les **5 derniers échanges** pour :
- Comprendre les questions de suivi ("Et ses Amazones ?")
- Maintenir la cohérence narrative
- Éviter les répétitions

**Limite** : 5 échanges pour ne pas saturer le contexte Gemini (limite tokens).


### Génération Audio TTS

**Technologie** : Microsoft Edge-TTS (cloud-based, gratuit)

**Voix utilisées** :
- **Français** : `fr-FR-DeniseNeural` (voix féminine chaleureuse)
- **Anglais** : `en-US-AriaNeural` (voix féminine claire)

**Pipeline audio** :
```
Texte généré → Edge-TTS → MP3 (bitrate 128kbps) → Stockage local → URL servie
```

**Optimisations** :
- Génération asynchrone (non-bloquant)
- Cache 24h (nettoyage automatique)
- Compression audio pour mobile


### Gestion des Sessions

**Stockage** : Mémoire Python (dictionnaire)

```python
SESSIONS = {
    "user-123": {
        "history": [...],  # 5 derniers échanges
        "language": "fr",
        "created_at": "2025-01-22T10:00:00Z"
    }
}
```

**Limitations** :
-  Données perdues au redémarrage du serveur
-  Pas de persistance base de données
-  Suffisant pour prototype/démonstration

**Amélioration future** : Redis ou PostgreSQL pour persistance.



##  Contributeurs

### Auteur principal
**AGBOSSOUNON Mariane**  
Étudiante en Licence IA - IFRI  

### Encadrement académique
- **Directeur de mémoire** : Msc. Ing. Marianne A. O. BALOGOUN
- **Institution** : IFRI (Institut de Formation et de Recherche en Informatique)



## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
