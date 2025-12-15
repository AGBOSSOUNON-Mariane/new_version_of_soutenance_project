"""
Script de vérification des modèles Gemini disponibles
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


def check_gemini_models():
    """Vérifie et affiche tous les modèles Gemini disponibles"""
    
    # Récupérer la clé API
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY non trouvée dans .env")
        print("\nPour obtenir une clé Gemini:")
        print("1. Allez sur https://makersuite.google.com/app/apikey")
        print("   ou https://aistudio.google.com/app/apikey")
        print("2. Créez une clé API (gratuit)")
        print("3. Ajoutez dans .env: GEMINI_API_KEY=votre_cle")
        return
    
    print("🔑 Clé API détectée")
    print(f"   {api_key[:20]}...{api_key[-10:]}")
    print()
    
    # Configurer Gemini
    try:
        genai.configure(api_key=api_key)
        print("✅ Connexion à Gemini réussie\n")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    # Lister les modèles
    print("="*80)
    print("📋 MODÈLES GEMINI DISPONIBLES")
    print("="*80)
    
    try:
        models = genai.list_models()
        
        # Filtrer pour ne garder que les modèles de génération
        generation_models = [
            m for m in models 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        if not generation_models:
            print("⚠️  Aucun modèle de génération trouvé")
            return
        
        print(f"\n✅ {len(generation_models)} modèle(s) de génération disponible(s)\n")
        
        for i, model in enumerate(generation_models, 1):
            print(f"{'─'*80}")
            print(f"📌 MODÈLE {i}: {model.name}")
            print(f"{'─'*80}")
            print(f"Nom complet: {model.name}")
            print(f"Nom court: {model.name.split('/')[-1]}")
            print(f"Description: {model.display_name}")
            
            # Limites
            if hasattr(model, 'input_token_limit'):
                print(f"Tokens entrée max: {model.input_token_limit:,}")
            if hasattr(model, 'output_token_limit'):
                print(f"Tokens sortie max: {model.output_token_limit:,}")
            
            # Méthodes supportées
            print(f"Méthodes: {', '.join(model.supported_generation_methods)}")
            print()
        
        # Recommandations
        print("="*80)
        print("💡 RECOMMANDATIONS")
        print("="*80)
        
        # Trouver les modèles recommandés
        flash_models = [m for m in generation_models if 'flash' in m.name.lower()]
        pro_models = [m for m in generation_models if 'pro' in m.name.lower()]
        
        if flash_models:
            print(f"\n🚀 RAPIDE & ÉCONOMIQUE:")
            for m in flash_models[:2]:
                print(f"   • {m.name.split('/')[-1]}")
        
        if pro_models:
            print(f"\n⭐ HAUTE QUALITÉ:")
            for m in pro_models[:2]:
                print(f"   • {m.name.split('/')[-1]}")
        
        print("\n📝 Pour votre projet (recommandé):")
        if flash_models:
            print(f"   → Utilisez: {flash_models[0].name.split('/')[-1]}")
            print(f"   → Raison: Rapide, gratuit, parfait pour RAG")
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des modèles: {e}")
        return


def test_simple_generation():
    """Test rapide de génération avec le modèle recommandé"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return
    
    print("\n" + "="*80)
    print("🧪 TEST DE GÉNÉRATION RAPIDE")
    print("="*80)
    
    try:
        genai.configure(api_key=api_key)
        
        # Essayer différents modèles
        model_names = [
            "gemini-2.5-flash",
            "gemini-2.5-pro"
        ]
        
        for model_name in model_names:
            try:
                print(f"\n🤖 Test avec: {model_name}")
                model = genai.GenerativeModel(model_name)
                
                response = model.generate_content("Dis bonjour en une phrase")
                
                print(f"✅ Fonctionne!")
                print(f"📝 Réponse: {response.text[:100]}...")
                print(f"\n👉 Utilisez ce modèle: '{model_name}'")
                break
                
            except Exception as e:
                print(f"❌ Erreur: {str(e)[:100]}...")
                continue
        
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    print("🚀 VÉRIFICATION DE GEMINI")
    print("="*80)
    print()
    
    # Vérifier les modèles
    check_gemini_models()
    
    # Test rapide
    choice = input("\n🧪 Voulez-vous tester la génération ? (o/n): ").strip().lower()
    if choice == 'o':
        test_simple_generation()
    
    print("\n✅ Vérification terminée!")