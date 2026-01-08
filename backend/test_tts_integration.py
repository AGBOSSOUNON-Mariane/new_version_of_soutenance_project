"""
Tests du système TTS + API
Vérifie le bon fonctionnement de la génération audio
"""

import requests
import json
from pathlib import Path


# Configuration
API_BASE_URL = "http://localhost:8000"
AUDIO_DIR = Path("audio_outputs")


def print_section(title: str):
    """Affiche une section"""
    print(f"\n{'='*80}")
    print(f"🧪 {title}")
    print(f"{'='*80}\n")


def test_health_check():
    """Test 1: Health check avec TTS"""
    print_section("TEST 1: Health Check")
    
    response = requests.get(f"{API_BASE_URL}/health")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    assert response.json()["services"]["tts"] == "operational"
    
    print("✅ Health check OK")


def test_chat_with_audio():
    """Test 2: Chat avec génération audio automatique"""
    print_section("TEST 2: Chat + Audio automatique")
    
    payload = {
        "message": "Bonjour Adjä ! Peux-tu me parler du roi Ghézo ?",
        "session_id": "test-session-123",
        "language": "fr",
        "generate_audio": True,
        "verbose": True
    }
    
    print(f"📤 Requête:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    
    print(f"\n📥 Réponse:")
    print(f"Status Code: {response.status_code}")
    
    data = response.json()
    
    print(f"\n💬 Texte: {data['response'][:200]}...")
    print(f"\n🔊 Audio:")
    print(f"   Disponible: {data['audio_available']}")
    
    if data['audio_available']:
        print(f"   URL: {data['audio_url']}")
        print(f"   Fichier: {data['audio_filename']}")
        print(f"   Durée: {data['audio_duration_seconds']}s")
        
        # Vérifier que le fichier existe
        audio_file = AUDIO_DIR / data['audio_filename']
        assert audio_file.exists(), f"❌ Fichier audio introuvable: {audio_file}"
        print(f"   ✅ Fichier audio vérifié: {audio_file}")
    
    assert response.status_code == 200
    assert data['success'] == True
    
    print("\n✅ Chat + Audio OK")


def test_chat_without_audio():
    """Test 3: Chat SANS génération audio"""
    print_section("TEST 3: Chat sans audio")
    
    payload = {
        "message": "Merci pour ces informations !",
        "session_id": "test-session-123",
        "generate_audio": False  # 🔕 Pas d'audio
    }
    
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    data = response.json()
    
    print(f"💬 Réponse: {data['response']}")
    print(f"🔊 Audio disponible: {data['audio_available']}")
    
    assert data['audio_available'] == False
    assert data['audio_url'] is None
    
    print("✅ Chat sans audio OK")


def test_generate_audio_standalone():
    """Test 4: Génération audio standalone (sans chat)"""
    print_section("TEST 4: Génération audio standalone")
    
    payload = {
        "text": "Ceci est un test de génération audio indépendante pour Adjä.",
        "language": "fr",
        "force_regenerate": False
    }
    
    response = requests.post(f"{API_BASE_URL}/generate-audio", json=payload)
    data = response.json()
    
    print(f"📥 Réponse:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    assert response.status_code == 200
    assert data['success'] == True
    assert data['audio_url'] is not None
    
    print("✅ Génération audio standalone OK")


def test_audio_cache():
    """Test 5: Vérification du cache audio"""
    print_section("TEST 5: Cache audio")
    
    # Première génération
    payload = {
        "text": "Test de cache audio pour Adjä.",
        "language": "fr",
        "force_regenerate": False
    }
    
    print("📤 Première génération...")
    response1 = requests.post(f"{API_BASE_URL}/generate-audio", json=payload)
    data1 = response1.json()
    
    print(f"   Caché: {data1['cached']}")
    assert data1['cached'] == False, "Première génération devrait ne PAS être cachée"
    
    # Deuxième génération (même texte)
    print("\n📤 Deuxième génération (même texte)...")
    response2 = requests.post(f"{API_BASE_URL}/generate-audio", json=payload)
    data2 = response2.json()
    
    print(f"   Caché: {data2['cached']}")
    assert data2['cached'] == True, "Deuxième génération devrait être cachée"
    
    # Vérifier que c'est le même fichier
    assert data1['audio_filename'] == data2['audio_filename']
    
    print("✅ Cache audio fonctionne correctement")


def test_english_audio():
    """Test 6: Audio en anglais"""
    print_section("TEST 6: Audio anglais")
    
    payload = {
        "message": "Hello Adjä! Tell me about the Amazons of Dahomey.",
        "session_id": "test-session-en",
        "language": "en",
        "generate_audio": True
    }
    
    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
    data = response.json()
    
    print(f"💬 Réponse: {data['response'][:150]}...")
    print(f"\n🔊 Audio:")
    print(f"   Langue: {data['language']}")
    print(f"   URL: {data.get('audio_url')}")
    
    assert data['language'] == 'en'
    assert data['audio_available'] == True
    
    print("✅ Audio anglais OK")


def test_audio_cleanup():
    """Test 7: Nettoyage des fichiers audio"""
    print_section("TEST 7: Nettoyage audio")
    
    # Compter les fichiers avant
    files_before = len(list(AUDIO_DIR.glob("*.mp3")))
    print(f"📊 Fichiers audio avant nettoyage: {files_before}")
    
    # Nettoyage (garder max 5 fichiers pour le test)
    response = requests.post(f"{API_BASE_URL}/audio/cleanup?max_files=5")
    data = response.json()
    
    print(f"\n📥 Résultat nettoyage:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    files_after = len(list(AUDIO_DIR.glob("*.mp3")))
    print(f"\n📊 Fichiers audio après nettoyage: {files_after}")
    
    assert response.status_code == 200
    assert files_after <= 5
    
    print("✅ Nettoyage OK")


def run_all_tests():
    """Lance tous les tests"""
    print("\n" + "="*80)
    print("🚀 TESTS COMPLETS DU SYSTÈME TTS + API")
    print("="*80)
    
    try:
        test_health_check()
        test_chat_with_audio()
        test_chat_without_audio()
        test_generate_audio_standalone()
        test_audio_cache()
        test_english_audio()
        test_audio_cleanup()
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS RÉUSSIS !")
        print("="*80)
        
    except AssertionError as e:
        print(f"\n❌ TEST ÉCHOUÉ: {e}")
    except requests.exceptions.ConnectionError:
        print("\n❌ ERREUR: Impossible de se connecter à l'API")
        print("   Assurez-vous que l'API est démarrée sur http://localhost:8000")
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")


if __name__ == "__main__":
    print("📋 Prérequis:")
    print("   1. L'API doit être lancée: python api_with_tts.py")
    print("   2. Le dossier audio_outputs/ doit exister")
    print("\nAppuyez sur Entrée pour commencer les tests...")
    input()
    
    run_all_tests()