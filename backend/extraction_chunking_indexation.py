import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import docx
import unicodedata
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

def normalize_id(text: str) -> str:
    # Enlever accents
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Remplacer tout caractère non-alphanumérique par _
    text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    return text

# Charger les variables d'environnement
load_dotenv()

class BeninHeritageIndexer:
    """
    Système d'extraction, chunking et indexation pour le patrimoine béninois
    """
    
    def __init__(self, pinecone_api_key: str, index_name: str = "benin-heritage"):
        """
        Initialise l'indexeur
        
        Args:
            pinecone_api_key: Clé API Pinecone
            index_name: Nom de l'index Pinecone
        """
        self.index_name = index_name
        
        # Initialiser Pinecone
        self.pc = Pinecone(api_key=pinecone_api_key)
        
        # Initialiser le modèle d'embeddings
        print(" Chargement du modèle d'embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialiser le text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        print(" Indexeur initialisé")
    
    def extract_text_from_docx(self, docx_path: str) -> Dict[str, Any]:
        """
        Extrait le texte et les métadonnées d'un document Word
        
        Args:
            docx_path: Chemin vers le fichier .docx
            
        Returns:
            Dict contenant le texte, les sections et les sources
        """
        try:
            doc = docx.Document(docx_path)
            full_text = []
            sources = []
            current_section = "Introduction"
            sections = {}
            in_sources = False
            
            for para in doc.paragraphs:
                text = para.text.strip()
                
                if not text:
                    continue
                
                # Détecter la section "Sources et références"

                if "source" in text.lower() and "référence" in text.lower():
                    in_sources = True
                    current_section = "Sources et références"
                    continue

                
                # Détecter les nouvelles sections (numérotées comme "1.", "2.", etc.)
                section_match = re.match(r'^(\d+)\.\s+(.+)$', text)
                if section_match:
                    current_section = section_match.group(2)
                    in_sources = False
                
                # Collecter les sources
                if in_sources:
                    # Nettoyer et ajouter les sources
                    if text.startswith('•') or text.startswith('-') or 'http' in text:
                        sources.append(text.lstrip('•-').strip())
                else:
                    # Ajouter le texte à la section courante
                    full_text.append(text)
                    if current_section not in sections:
                        sections[current_section] = []
                    sections[current_section].append(text)
            
            return {
                'text': '\n\n'.join(full_text),
                'sections': sections,
                'sources': sources
            }
            
        except Exception as e:
            print(f" Erreur lors de l'extraction de {docx_path}: {e}")
            return {'text': '', 'sections': {}, 'sources': []}
    
    def find_related_images(self, docx_path: str) -> List[str]:
        """
        Trouve toutes les images dans le même dossier que le document Word
        
        Args:
            docx_path: Chemin vers le fichier .docx
            
        Returns:
            Liste des chemins d'images relatifs
        """
        docx_dir = Path(docx_path).parent
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        
        images = []
        for file in docx_dir.iterdir():
            if file.suffix.lower() in image_extensions:
                images.append(str(file))
        
        return images
    
    def extract_location_hierarchy(self, file_path: str) -> Dict[str, str]:
        """
        Extrait la hiérarchie de localisation depuis le chemin du fichier
        
        Args:
            file_path: Chemin complet du fichier
            
        Returns:
            Dict avec pole, category, subcategory
        """
        parts = Path(file_path).parts
        
        # Trouver l'index de "Donnees_soutenance"
        try:
            base_idx = parts.index("Donnees_soutenance")
        except ValueError:
            return {'pole': 'Unknown', 'category': '', 'subcategory': ''}
        
        hierarchy = {
            'pole': parts[base_idx + 1] if len(parts) > base_idx + 1 else 'Unknown',
            'category': parts[base_idx + 2] if len(parts) > base_idx + 2 else '',
            'subcategory': parts[base_idx + 3] if len(parts) > base_idx + 3 else ''
        }
        
        return hierarchy
    
    def process_document(self, docx_path: str) -> List[Dict[str, Any]]:
        """
        Traite un document: extraction, chunking, préparation des métadonnées
        
        Args:
            docx_path: Chemin vers le fichier .docx
            
        Returns:
            Liste de chunks avec métadonnées
        """
        print(f"Traitement de: {Path(docx_path).name}")
        
        # Extraire le texte et les métadonnées
        extracted = self.extract_text_from_docx(docx_path)
        
        if not extracted['text']:
            print(f" Aucun texte extrait de {docx_path}")
            return []
        
        # Trouver les images associées
        images = self.find_related_images(docx_path)
        
        # Extraire la hiérarchie de localisation
        location = self.extract_location_hierarchy(docx_path)
        
        # Découper le texte en chunks
        chunks = self.text_splitter.split_text(extracted['text'])
        
        # Préparer les documents avec métadonnées
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                'text': chunk,
                'metadata': {
                    'source_file': str(Path(docx_path).name),
                    'source_path': str(docx_path),
                    'pole': location['pole'],
                    'category': location['category'],
                    'subcategory': location['subcategory'],
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'images': images,
                    'sources': extracted['sources'],
                    'sections': list(extracted['sections'].keys())
                }
            }
            documents.append(doc)
        
        print(f" {len(chunks)} chunks créés")
        return documents
    
    def process_all_documents(self, base_path: str) -> List[Dict[str, Any]]:
        """
        Traite tous les documents .docx dans le dossier de base
        
        Args:
            base_path: Chemin vers le dossier "Donnees_soutenance"
            
        Returns:
            Liste de tous les documents traités
        """
        all_documents = []
        base_path = Path(base_path)
        
        # Trouver tous les fichiers .docx
        docx_files = list(base_path.rglob("*.docx"))
        
        # Filtrer les fichiers temporaires Word (commencent par ~$)
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        
        print(f" {len(docx_files)} documents Word trouvés")
        print("=" * 60)
        
        for docx_file in docx_files:
            documents = self.process_document(str(docx_file))
            all_documents.extend(documents)
        
        print("=" * 60)
        print(f" Total: {len(all_documents)} chunks créés à partir de {len(docx_files)} documents")
        
        return all_documents
    

    def save_chunks_to_json(self, documents: List[Dict[str, Any]], output_dir: str = "chunks_backup"):
        """
        Sauvegarde tous les chunks dans un fichier JSON
        
        Args:
            documents: Liste des documents/chunks
            output_dir: Dossier de sauvegarde
        """
        # Créer le dossier si nécessaire
        os.makedirs(output_dir, exist_ok=True)
        
        # Préparer les données pour JSON
        chunks_data = []
        for doc in documents:
            chunks_data.append({
                'text': doc['text'],
                'metadata': doc['metadata']
            })
        
        # Nom de fichier avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"chunks_{timestamp}.json")
        
        # Sauvegarder
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ Chunks sauvegardés dans: {output_file}")
        print(f"  📊 Total: {len(chunks_data)} chunks")
        
        return output_file
    
    def create_pinecone_index(self, dimension: int = 384):
        """
        Crée l'index Pinecone s'il n'existe pas
        
        Args:
            dimension: Dimension des embeddings (384 pour all-MiniLM-L6-v2)
        """
        # Vérifier si l'index existe déjà
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name in existing_indexes:
            print(f" L'index '{self.index_name}' existe déjà")
            return
        
        print(f" Création de l'index '{self.index_name}'...")
        
        # Créer l'index avec Serverless
        self.pc.create_index(
            name=self.index_name,
            dimension=dimension,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        
        print(f" Index '{self.index_name}' créé")
    
    def index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100):
        """
        Indexe les documents dans Pinecone
        
        Args:
            documents: Liste des documents à indexer
            batch_size: Taille des lots pour l'indexation
        """
        if not documents:
            print("  Aucun document à indexer")
            return
        
        # Récupérer l'index
        index = self.pc.Index(self.index_name)
        
        print(f" Indexation de {len(documents)} chunks...")
        
        # Traiter par lots
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Générer les embeddings pour le lot
            texts = [doc['text'] for doc in batch]
            embeddings = self.embeddings.embed_documents(texts)
            
            # Préparer les vecteurs pour Pinecone
            vectors = []
            for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                file_ascii = normalize_id(doc['metadata']['source_file'])
                vector_id = f"{file_ascii}_{doc['metadata']['chunk_index']}"

                
                # Pinecone accepte des métadonnées simples (pas de listes complexes)
                # On convertit les listes en chaînes
                metadata = {
                    'text': doc['text'][:1000],  # Limiter la longueur
                    'source_file': doc['metadata']['source_file'],
                    'source_path': doc['metadata']['source_path'],
                    'pole': doc['metadata']['pole'],
                    'category': doc['metadata']['category'],
                    'subcategory': doc['metadata']['subcategory'],
                    'chunk_index': doc['metadata']['chunk_index'],
                    'total_chunks': doc['metadata']['total_chunks'],
                    'images': '|'.join(doc['metadata']['images'][:10]),  # Max 10 images
                    'sources': '|'.join(doc['metadata']['sources'][:5]),  # Max 5 sources
                    'sections': '|'.join(doc['metadata']['sections'][:10])  # Max 10 sections
                }
                
                vectors.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': metadata
                })
            
            # Upserter dans Pinecone
            index.upsert(vectors=vectors)
            
            print(f"   Lot {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1} indexé")
        
        print(f" Indexation terminée!")
        
        # Afficher les statistiques
        stats = index.describe_index_stats()
        print(f" Statistiques de l'index:")
        print(f"   - Vecteurs totaux: {stats['total_vector_count']}")
    
    def run_full_pipeline(self, base_path: str):
        """
        Exécute le pipeline complet: extraction, chunking, indexation
        
        Args:
            base_path: Chemin vers le dossier "Donnees_soutenance"
        """
        print(" DÉMARRAGE DU PIPELINE COMPLET")
        print("=" * 60)
        
        # 1. Créer l'index Pinecone
        print("\n ÉTAPE 1: Création de l'index Pinecone")
        self.create_pinecone_index()
        
        # 2. Traiter tous les documents
        print("\n ÉTAPE 2: Extraction et chunking des documents")
        documents = self.process_all_documents(base_path)

        # 3. SAUVEGARDE DES CHUNKS EN JSON (NOUVEAU)
        print("\n ÉTAPE 3: Sauvegarde des chunks en JSON")
        json_file = self.save_chunks_to_json(documents)
        
        # 3. Indexer dans Pinecone
        print("\n ÉTAPE 3: Indexation dans Pinecone")
        self.index_documents(documents)
        
        print("\n" + "=" * 60)
        print(" PIPELINE TERMINÉ AVEC SUCCÈS!")
        print(f" 📁 Backup JSON: {json_file}")
        print("=" * 60)


if __name__ == "__main__":
    # Charger les configurations depuis .env
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    BASE_PATH = os.getenv("BASE_PATH")
    INDEX_NAME = os.getenv("INDEX_NAME", "benin-heritage")  # Valeur par défaut
    
    # Vérifier que les variables sont définies
    if not PINECONE_API_KEY:
        raise ValueError(" PINECONE_API_KEY non définie dans le fichier .env")
    
    if not BASE_PATH:
        raise ValueError(" BASE_PATH non défini dans le fichier .env")
    
    if not os.path.exists(BASE_PATH):
        raise ValueError(f" Le chemin {BASE_PATH} n'existe pas")
    
    print(f" Configuration chargée depuis .env")
    print(f"   - Index: {INDEX_NAME}")
    print(f"   - Base path: {BASE_PATH}")
    print()
    
    # Créer l'indexeur
    indexer = BeninHeritageIndexer(
        pinecone_api_key=PINECONE_API_KEY,
        index_name=INDEX_NAME
    )
    
    # Exécuter le pipeline complet
    indexer.run_full_pipeline(BASE_PATH)
    
   