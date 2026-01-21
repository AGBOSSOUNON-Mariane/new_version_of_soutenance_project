"""
Test de conversion audio avec nouveau texte
"""

from tts_service import TTSService

print("\n🧪 TEST DE CONVERSION AUDIO")
print("="*80)

service = TTSService()

# Nouveau texte unique pour éviter le cache
test_text = "Ceci est un test de conversion audio pour Android. Le roi Ghézo était un grand souverain."

print("\n📝 Génération d'un NOUVEAU fichier audio...")
result = service.generate_audio(
    text=test_text,
    language="fr",
    force_regenerate=True  # ← Force la régénération même si le fichier existe
)

print("\n✅ RÉSULTAT:")
print(f"   Succès: {result['success']}")
print(f"   Fichier: {result['audio_filename']}")
print(f"   Durée: {result['duration_seconds']}s")
print(f"   Caché: {result['cached']}")
print(f"   Converti: {result.get('converted', 'N/A')}")

if result.get('converted') == True:
    print("\n🎉 PARFAIT ! La conversion audio fonctionne !")
    print("   → Les fichiers audio sont maintenant compatibles Android")
else:
    print("\n⚠️ Conversion non effectuée")
    print("   → Vérifie que ffmpeg est bien dans le PATH")