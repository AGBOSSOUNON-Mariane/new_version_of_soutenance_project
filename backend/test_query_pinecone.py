from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv


load_dotenv() 

# Config Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "benin-heritage"

# Initialiser Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# Initialiser le modèle d'embeddings pour la requête
embeddings_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)

# Requête texte
query_text = "Qui était le roi Ghézo et quels étaient ses symboles ?"

# Créer l'embedding pour la requête
query_vector = embeddings_model.embed_query(query_text)

# Faire la recherche dans Pinecone
results = index.query(
    vector=query_vector,
    top_k=5,  # nombre de chunks les plus proches
    include_metadata=True
)

# Parcourir les résultats et extraire texte + images + sources
for match in results['matches']:
    metadata = match['metadata']
    text = metadata.get('text', '')
    # Convertir les chaînes séparées par '|' en listes
    images = metadata.get('images', '').split('|') if metadata.get('images') else []
    sources = metadata.get('sources', '').split('|') if metadata.get('sources') else []

    print("=== Chunk trouvé ===")
    print("Texte :", text)
    print("Images :", images)
    print("Sources :", sources)
    print("\n")
