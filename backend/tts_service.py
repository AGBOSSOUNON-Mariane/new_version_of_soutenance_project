"""
Service TTS (Text-to-Speech) pour l'agent Adjä
Génération d'audio à partir des réponses textuelles
Utilise gTTS (Google Text-to-Speech) - Gratuit
"""

import os
import io
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from gtts import gTTS
from pydantic import BaseModel


class TTSConfig:
    """Configuration du service TTS"""
    
    # Dossier de stockage des fichiers audio
    AUDIO_OUTPUT_DIR = Path("audio_outputs")
    
    # Langues supportées (codes gTTS)
    SUPPORTED_LANGUAGES = {
        "fr": "fr",  # Français
        "en": "en"   # Anglais
    }
    
    # Paramètres gTTS
    SLOW_SPEECH = False  # False = vitesse normale, True = lent
    
    # Cache (optionnel)
    ENABLE_CACHE = True  # Éviter de régénérer les mêmes audios
    
    def __init__(self):
        """Crée le dossier audio si nécessaire"""
        self.AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)


class AudioResponse(BaseModel):
    """Modèle de réponse audio"""
    success: bool
    audio_path: Optional[str] = None
    audio_filename: Optional[str] = None
    audio_url: Optional[str] = None  # Pour l'API
    duration_seconds: Optional[float] = None
    text_length: int
    language: str
    cached: bool = False
    error: Optional[str] = None


class TTSService:
    """
    Service de génération audio Text-to-Speech
    Utilise gTTS pour convertir le texte en audio MP3
    """
    
    def __init__(self, config: Optional[TTSConfig] = None):
        """
        Initialise le service TTS
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or TTSConfig()
        print(f"🔊 Service TTS initialisé")
        print(f"   📁 Dossier audio: {self.config.AUDIO_OUTPUT_DIR}")
        print(f"   💾 Cache activé: {self.config.ENABLE_CACHE}")
    
    def _generate_audio_filename(self, text: str, language: str) -> str:
        """
        Génère un nom de fichier unique basé sur le hash du texte
        Permet le cache : même texte = même fichier
        
        Args:
            text: Texte à convertir
            language: Code langue
            
        Returns:
            Nom de fichier (ex: "abc123def_fr.mp3")
        """
        # Hash MD5 du texte pour unicité
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
        return f"{text_hash}_{language}.mp3"
    
    def _get_audio_path(self, filename: str) -> Path:
        """Retourne le chemin complet du fichier audio"""
        return self.config.AUDIO_OUTPUT_DIR / filename
    
    def _file_exists(self, filename: str) -> bool:
        """Vérifie si un fichier audio existe déjà (cache)"""
        return self._get_audio_path(filename).exists()
    
    def generate_audio(
            
        self,
        text: str,
        language: str = "fr",
        force_regenerate: bool = False
    ) -> Dict:
        """
        Génère un fichier audio à partir du texte
        
        Returns:
            Dict avec success, audio_path, audio_filename, duration_seconds, etc.
        """
        
        # Validation texte vide
        if not text or not text.strip():
            return {
                "success": False,
                "audio_path": None,
                "audio_filename": None,
                "duration_seconds": None,
                "text_length": 0,
                "language": language,
                "cached": False,
                "error": "Texte vide"
            }
        
        text_clean = text.strip()
        
        # Vérifier langue supportée
        if language not in self.config.SUPPORTED_LANGUAGES:
            return {
                "success": False,
                "audio_path": None,
                "audio_filename": None,
                "duration_seconds": None,
                "text_length": len(text_clean),
                "language": language,
                "cached": False,
                "error": f"Langue '{language}' non supportée. Langues disponibles: {list(self.config.SUPPORTED_LANGUAGES.keys())}"
            }
        
        try:
            # Générer nom de fichier
            filename = self._generate_audio_filename(text_clean, language)
            audio_path = self._get_audio_path(filename)
            
            # Vérifier cache
            if self.config.ENABLE_CACHE and not force_regenerate and self._file_exists(filename):
                print(f"🔊 Audio déjà en cache: {filename}")
                duration = self._estimate_duration(text_clean, language)
                
                return {
                    "success": True,
                    "audio_path": str(audio_path),
                    "audio_filename": filename,
                    "duration_seconds": duration,
                    "text_length": len(text_clean),
                    "language": language,
                    "cached": True  # ✅ C'est du cache ici
                }
            
            # Générer l'audio avec gTTS
            print(f"🔊 Génération audio: {filename}...")
            
            tts = gTTS(
                text=text_clean,
                lang=self.config.SUPPORTED_LANGUAGES[language],
                slow=self.config.SLOW_SPEECH
            )
            
            # Sauvegarder
            tts.save(str(audio_path))
            
            print(f"✅ Audio généré: {audio_path}")
            
            # Calculer durée
            duration = self._estimate_duration(text_clean, language)
            
            return {
                "success": True,
                "audio_path": str(audio_path),
                "audio_filename": filename,
                "duration_seconds": duration,
                "text_length": len(text_clean),
                "language": language,
                "cached": False  # ✅ Nouveau fichier
            }
            
        except Exception as e:
            print(f"❌ Erreur génération audio: {e}")
            return {
                "success": False,
                "audio_path": None,
                "audio_filename": None,
                "duration_seconds": None,
                "text_length": len(text_clean),
                "language": language,
                "cached": False,
                "error": str(e)
            }
    
    def _estimate_duration(self, text: str, language: str) -> float:
        """
        Estime la durée approximative de l'audio
        Basé sur le nombre de mots et la vitesse de parole moyenne
        
        Args:
            text: Texte
            language: Langue
            
        Returns:
            Durée estimée en secondes
        """
        # Vitesse de parole moyenne (mots par minute)
        # Français: ~160 mots/min, Anglais: ~150 mots/min
        wpm = 160 if language == "fr" else 150
        
        # Compter les mots
        word_count = len(text.split())
        
        # Durée = (nb_mots / vitesse) * 60
        duration = (word_count / wpm) * 60
        
        return round(duration, 2)
    
    def generate_audio_stream(self, text: str, language: str = "fr") -> Optional[io.BytesIO]:
        """
        Génère l'audio en mémoire (pour streaming API)
        
        Args:
            text: Texte à convertir
            language: Code langue
            
        Returns:
            BytesIO contenant l'audio MP3, ou None si erreur
        """
        if not text or not text.strip():
            return None
        
        try:
            tts = gTTS(
                text=text.strip(),
                lang=self.config.SUPPORTED_LANGUAGES.get(language, "fr"),
                slow=self.config.SLOW_SPEECH
            )
            
            # Générer en mémoire
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return audio_buffer
            
        except Exception as e:
            print(f"❌ Erreur génération stream audio: {e}")
            return None
    
    def cleanup_old_files(self, max_files: int = 100):
        """
        Nettoie les vieux fichiers audio (maintenance)
        Garde seulement les N fichiers les plus récents
        
        Args:
            max_files: Nombre maximum de fichiers à garder
        """
        try:
            audio_files = sorted(
                self.config.AUDIO_OUTPUT_DIR.glob("*.mp3"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            if len(audio_files) > max_files:
                files_to_delete = audio_files[max_files:]
                
                for file in files_to_delete:
                    file.unlink()
                    print(f"🗑️ Supprimé: {file.name}")
                
                print(f"✅ Nettoyage: {len(files_to_delete)} fichiers supprimés")
            else:
                print(f"✅ Nettoyage: Aucun fichier à supprimer ({len(audio_files)}/{max_files})")
                
        except Exception as e:
            print(f"❌ Erreur nettoyage: {e}")


# =============================================================================
# TESTS
# =============================================================================

def test_tts_service():
    """Tests du service TTS"""
    
    print("\n🧪 TESTS DU SERVICE TTS")
    print("="*80)
    
    service = TTSService()
    
    # Test 1 : Génération français
    print("\n📝 Test 1: Génération audio français")
    result_fr = service.generate_audio(
        "Bonjour ! Je suis Adjä, guide culturelle virtuelle. "
        "Laisse-moi te raconter l'histoire fascinante du roi Ghézo.",
        language="fr"
    )
    
    print(f"✅ Résultat:")
    print(f"   Succès: {result_fr.success}")
    print(f"   Fichier: {result_fr.audio_filename}")
    print(f"   Durée estimée: {result_fr.duration_seconds}s")
    print(f"   Caché: {result_fr.cached}")
    
    # Test 2 : Génération anglais
    print("\n📝 Test 2: Génération audio anglais")
    result_en = service.generate_audio(
        "Hello! I am Adjä, your virtual cultural guide. "
        "Let me tell you the fascinating story of King Ghezo.",
        language="en"
    )
    
    print(f"✅ Résultat:")
    print(f"   Succès: {result_en.success}")
    print(f"   Fichier: {result_en.audio_filename}")
    print(f"   Durée estimée: {result_en.duration_seconds}s")
    
    # Test 3 : Cache (régénérer le même texte)
    print("\n📝 Test 3: Vérification du cache")
    result_cache = service.generate_audio(
        "Bonjour ! Je suis Adjä, guide culturelle virtuelle. "
        "Laisse-moi te raconter l'histoire fascinante du roi Ghézo.",
        language="fr"
    )
    
    print(f"✅ Résultat:")
    print(f"   Caché: {result_cache.cached}")
    print(f"   (Devrait être True)")
    
    # Test 4 : Erreur (texte vide)
    print("\n📝 Test 4: Gestion d'erreur (texte vide)")
    result_error = service.generate_audio("", language="fr")
    
    print(f"✅ Résultat:")
    print(f"   Succès: {result_error.success}")
    print(f"   Erreur: {result_error.error}")
    
    print("\n✅ TESTS TERMINÉS !")


if __name__ == "__main__":
    test_tts_service()