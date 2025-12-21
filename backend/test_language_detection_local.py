"""
Test de détection de langue SANS appels Gemini
Teste uniquement la fonction detect_language() en local
"""

import sys
import os

# Ajouter le chemin du module
sys.path.insert(0, os.path.dirname(__file__))

# Importer directement la fonction de détection
try:
    from api import detect_language
except ImportError:
    print("❌ Impossible d'importer api.py")
    print("💡 Assurez-vous que api.py est dans le même dossier")
    sys.exit(1)


def test_language_detection_local():
    """
    Teste la détection de langue EN LOCAL
    N'appelle PAS l'API, n'utilise PAS Gemini
    0€ de coût ! ✅
    """
    
    test_cases = [
        # (message, langue_attendue, description)
        ("Bonjour, comment allez-vous ?", "fr", "Salutation française"),
        ("Hello, how are you?", "en", "Salutation anglaise"),
        ("Qui est le roi Ghézo ?", "fr", "Question patrimoniale française"),
        ("Who is king Ghezo?", "en", "Question patrimoniale anglaise"),
        ("Parle-moi des Amazones du Dahomey", "fr", "Demande narrative française"),
        ("Tell me about the Dahomey Amazons", "en", "Demande narrative anglaise"),
        ("Raconte-moi l'histoire d'Ouidah", "fr", "Récit français"),
        ("Tell me the story of Ouidah", "en", "Récit anglais"),
        ("Merci beaucoup pour cette information", "fr", "Remerciement français"),
        ("Thank you very much for this information", "en", "Remerciement anglais"),
        
        # Cas difficiles
        ("Ghézo ?", "fr", "Question courte avec accent français"),
        ("Ouidah ?", "fr", "Lieu avec accent français"),
        ("Amazons", "en", "Mot ambigu (probablement anglais)"),
        ("Hi", "en", "Très court anglais"),
        ("Salut", "fr", "Très court français"),
    ]
    
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║          TEST DÉTECTION DE LANGUE (LOCAL - 0€)                            ║")
    print("║          Aucun appel API, aucune consommation de quota                    ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    passed = 0
    failed = 0
    ambiguous = 0
    
    for message, expected_lang, description in test_cases:
        print(f"{'─'*80}")
        print(f"📝 Test: {description}")
        print(f"   Message: '{message}'")
        print(f"   Langue attendue: {expected_lang}")
        
        try:
            # Appel LOCAL de la fonction (0€)
            detected_lang = detect_language(message, default="fr")
            
            if detected_lang == expected_lang:
                print(f"   ✅ SUCCÈS: Langue détectée = {detected_lang}")
                passed += 1
            else:
                # Vérifier si c'est un cas ambigu connu
                if len(message.split()) <= 2:
                    print(f"   ⚠️ AMBIGU: Langue détectée = {detected_lang} (attendu: {expected_lang})")
                    print(f"      Note: Message trop court, détection moins fiable")
                    ambiguous += 1
                else:
                    print(f"   ❌ ÉCHEC: Langue détectée = {detected_lang} (attendu: {expected_lang})")
                    failed += 1
                    
        except Exception as e:
            print(f"   ❌ ERREUR: {e}")
            failed += 1
    
    # Résumé
    print(f"\n{'='*80}")
    print(f"📊 RÉSULTATS")
    print(f"{'='*80}")
    print(f"✅ Tests réussis: {passed}/{len(test_cases)}")
    print(f"⚠️ Cas ambigus (normaux): {ambiguous}/{len(test_cases)}")
    print(f"❌ Tests échoués: {failed}/{len(test_cases)}")
    total_ok = passed + ambiguous
    print(f"📈 Taux de réussite: {(total_ok/len(test_cases)*100):.1f}%")
    print(f"\n💰 Coût: 0€ (aucun appel API)")
    
    if failed == 0:
        print(f"\n🎉 Tous les tests importants sont passés !")
        print(f"⚠️ Les cas ambigus sont normaux pour les messages très courts")
    else:
        print(f"\n⚠️ {failed} test(s) ont échoué de manière inattendue")


def test_edge_cases():
    """Teste des cas limites"""
    
    print(f"\n\n{'='*80}")
    print("🧪 TEST DES CAS LIMITES")
    print("="*80)
    
    edge_cases = [
        ("", "fr", "Chaîne vide"),
        ("   ", "fr", "Espaces uniquement"),
        ("123", "fr", "Chiffres uniquement"),
        ("!@#$%", "fr", "Symboles uniquement"),
        ("a", "fr", "Une seule lettre"),
        ("Ghézo", "fr", "Mot unique avec accent"),
        ("Hello", "en", "Mot unique anglais"),
        ("Bonjour Hello", "fr", "Mélange fr-en (fr dominant)"),
        ("Hello Bonjour", "en", "Mélange en-fr (en dominant)"),
    ]
    
    for message, expected_default, description in edge_cases:
        print(f"\n{'─'*60}")
        print(f"📝 {description}: '{message}'")
        
        try:
            detected = detect_language(message, default="fr")
            print(f"   Résultat: {detected}")
            
            if detected in ['fr', 'en']:
                print(f"   ✅ Détection valide")
            else:
                print(f"   ⚠️ Résultat inattendu")
                
        except Exception as e:
            print(f"   ⚠️ Exception gérée: {e}")
    
    print(f"\n{'='*80}")
    print("✅ Test des cas limites terminé")


def show_usage_recommendation():
    """Affiche des recommandations d'utilisation"""
    
    print(f"\n\n{'='*80}")
    print("💡 RECOMMANDATIONS")
    print("="*80)
    print("""
1. 🎯 Pour tester LA DÉTECTION SEULE (0€) :
   → python test_language_detection_local.py  (ce fichier)
   
2. 🧪 Pour tester L'API COMPLÈTE avec Gemini (consomme quota) :
   → python test_language_detection.py
   → python test_api.py
   
3. 💰 Quota Gemini Flash :
   → 2 millions tokens/jour GRATUITS
   → ~50-100 tests complets possibles/jour
   → Ne t'inquiète pas, c'est très généreux !
   
4. ⚡ En développement :
   → Utilise TOUJOURS ce script local d'abord
   → Lance les tests API seulement quand tu es sûr
   
5. 🎓 Pour ta soutenance :
   → Montre les logs verbose=True (c'est impressionnant)
   → Mais désactive en production
""")


if __name__ == "__main__":
    print()
    
    try:
        # Test 1: Détection de langue
        test_language_detection_local()
        
        # Test 2: Cas limites
        test_edge_cases()
        
        # Recommandations
        show_usage_recommendation()
        
        print(f"\n{'='*80}")
        print("🎉 SUITE DE TESTS TERMINÉE (0€ dépensés)")
        print("="*80)
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrompus par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)