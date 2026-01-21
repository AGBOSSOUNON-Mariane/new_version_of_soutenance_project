"""
Service TTS (Text-to-Speech) pour l'agent Adjä
Génération d'audio à partir des réponses textuelles
Utilise gTTS (Google Text-to-Speech) - Gratuit
VERSION AMÉLIORÉE avec conversion audio compatible Android/iOS
"""

import os
import io
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from gtts import gTTS
from pydantic import BaseModel

# 🆕 Import pour conversion audio
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub non installé - conversion audio désactivée")
    print("   Pour l'activer: pip install pydub")
    print("   Et installer ffmpeg: https://ffmpeg.org/download.html")


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
    
    # 🆕 Conversion audio (pour compatibilité Android/iOS)
    ENABLE_CONVERSION = True  # Active la conversion automatique
    
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
    🆕 Avec conversion automatique pour Android/iOS
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
        
        # 🆕 Vérifier disponibilité de la conversion
        if self.config.ENABLE_CONVERSION and not PYDUB_AVAILABLE:
            print(f"   ⚠️ Conversion audio désactivée (pydub manquant)")
            self.config.ENABLE_CONVERSION = False
        else:
            print(f"   🔄 Conversion audio: {self.config.ENABLE_CONVERSION}")
    
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
    
    def _convert_audio_to_compatible_format(self, input_path: Path, output_path: Path) -> bool:
        """
        🆕 Convertit l'audio MP3 en format compatible Android/iOS
        
        Paramètres optimaux pour ExoPlayer (Android) :
        - Codec: libmp3lame
        - Bitrate: 128k
        - Sample rate: 44100 Hz
        - Channels: 1 (mono pour voix)
        
        Args:
            input_path: Fichier MP3 source (gTTS)
            output_path: Fichier MP3 converti
            
        Returns:
            True si conversion réussie, False sinon
        """
        if not PYDUB_AVAILABLE:
            # Pas de conversion, on garde l'original
            if input_path != output_path:
                input_path.rename(output_path)
            return False
        
        try:
            print(f"   🔄 Conversion en cours...")
            
            # Charger l'audio
            audio = AudioSegment.from_mp3(str(input_path))
            
            # Convertir en mono (économise de la bande passante + voix)
            audio = audio.set_channels(1)
            
            # Normaliser à 44.1kHz (standard)
            audio = audio.set_frame_rate(44100)
            
            # Exporter avec paramètres optimaux
            audio.export(
                str(output_path),
                format="mp3",
                bitrate="128k",
                parameters=["-codec:a", "libmp3lame", "-q:a", "2"]
            )
            
            # Supprimer le fichier temporaire
            if input_path.exists() and input_path != output_path:
                input_path.unlink()
            
            print(f"   ✅ Audio converti: {output_path.name}")
            return True
            
        except Exception as e:
            print(f"   ⚠️ Échec conversion: {e}")
            # Fallback : utiliser le fichier original
            if input_path.exists() and not output_path.exists():
                input_path.rename(output_path)
            return False
    
    def generate_audio(
        self,
        text: str,
        language: str = "fr",
        force_regenerate: bool = False
    ) -> Dict:
        """
        Génère un fichier audio à partir du texte
        🆕 Avec conversion automatique pour compatibilité mobile
        
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
                print(f"♻️ Audio en cache: {filename}")
                duration = self._estimate_duration(text_clean, language)
                
                return {
                    "success": True,
                    "audio_path": str(audio_path),
                    "audio_filename": filename,
                    "duration_seconds": duration,
                    "text_length": len(text_clean),
                    "language": language,
                    "cached": True
                }
            
            # 🆕 GÉNÉRATION AUDIO EN 2 ÉTAPES
            print(f"🔊 Génération audio: {filename}")
            
            # Étape 1 : Générer avec gTTS
            if self.config.ENABLE_CONVERSION:
                # Fichier temporaire si conversion activée
                temp_filename = f"{filename[:-4]}_temp.mp3"
                temp_path = self._get_audio_path(temp_filename)
            else:
                # Fichier final directement si pas de conversion
                temp_path = audio_path
            
            tts = gTTS(
                text=text_clean,
                lang=self.config.SUPPORTED_LANGUAGES[language],
                slow=self.config.SLOW_SPEECH
            )
            
            tts.save(str(temp_path))
            print(f"   ✅ Audio brut généré")
            
            # Étape 2 : Convertir si activé
            converted = False
            if self.config.ENABLE_CONVERSION:
                converted = self._convert_audio_to_compatible_format(temp_path, audio_path)
            
            # Calculer durée
            duration = self._estimate_duration(text_clean, language)
            
            print(f"✅ Audio prêt: {filename} ({duration}s)")
            
            return {
                "success": True,
                "audio_path": str(audio_path),
                "audio_filename": filename,
                "duration_seconds": duration,
                "text_length": len(text_clean),
                "language": language,
                "cached": False,
                "converted": converted  # 🆕 Info de conversion
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
        🆕 Avec conversion si disponible
        
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
            
            # 🆕 Conversion si disponible
            if self.config.ENABLE_CONVERSION and PYDUB_AVAILABLE:
                try:
                    # Convertir le buffer
                    audio = AudioSegment.from_mp3(audio_buffer)
                    audio = audio.set_channels(1).set_frame_rate(44100)
                    
                    # Exporter dans un nouveau buffer
                    final_buffer = io.BytesIO()
                    audio.export(final_buffer, format="mp3", bitrate="128k")
                    final_buffer.seek(0)
                    
                    return final_buffer
                except Exception as e:
                    print(f"⚠️ Conversion streaming échouée: {e}, utilisation original")
                    audio_buffer.seek(0)
                    return audio_buffer
            
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
            
            # 🆕 Exclure les fichiers temporaires
            audio_files = [f for f in audio_files if "_temp" not in f.name]
            
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
    
    print("\n🧪 TESTS DU SERVICE TTS (VERSION AMÉLIORÉE)")
    print("="*80)
    
    service = TTSService()
    
    # Test 1 : Génération français avec conversion
    print("\n📝 Test 1: Génération audio français (avec conversion)")
    result_fr = service.generate_audio(
        "Bonjour ! Je suis Adjä, guide culturelle virtuelle. "
        "Laisse-moi te raconter l'histoire fascinante du roi Ghézo.",
        language="fr"
    )
    
    print(f"\n✅ Résultat:")
    print(f"   Succès: {result_fr['success']}")
    print(f"   Fichier: {result_fr['audio_filename']}")
    print(f"   Durée estimée: {result_fr['duration_seconds']}s")
    print(f"   Caché: {result_fr['cached']}")
    print(f"   Converti: {result_fr.get('converted', False)}")
    
    # Test 2 : Génération anglais
    print("\n📝 Test 2: Génération audio anglais")
    result_en = service.generate_audio(
        "Hello! I am Adjä, your virtual cultural guide. "
        "Let me tell you the fascinating story of King Ghezo.",
        language="en"
    )
    
    print(f"\n✅ Résultat:")
    print(f"   Succès: {result_en['success']}")
    print(f"   Fichier: {result_en['audio_filename']}")
    print(f"   Durée estimée: {result_en['duration_seconds']}s")
    print(f"   Converti: {result_en.get('converted', False)}")
    
    # Test 3 : Cache (régénérer le même texte)
    print("\n📝 Test 3: Vérification du cache")
    result_cache = service.generate_audio(
        "Bonjour ! Je suis Adjä, guide culturelle virtuelle. "
        "Laisse-moi te raconter l'histoire fascinante du roi Ghézo.",
        language="fr"
    )
    
    print(f"\n✅ Résultat:")
    print(f"   Caché: {result_cache['cached']}")
    print(f"   (Devrait être True car même texte)")
    
    # Test 4 : Erreur (texte vide)
    print("\n📝 Test 4: Gestion d'erreur (texte vide)")
    result_error = service.generate_audio("", language="fr")
    
    print(f"\n✅ Résultat:")
    print(f"   Succès: {result_error['success']}")
    print(f"   Erreur: {result_error['error']}")
    
    # 🆕 Test 5 : Vérifier compatibilité
    print("\n📝 Test 5: Vérification compatibilité Android")
    if PYDUB_AVAILABLE:
        print("   ✅ pydub installé - Conversion activée")
        print("   ✅ Les fichiers audio devraient fonctionner sur Android")
    else:
        print("   ⚠️ pydub NON installé - Conversion désactivée")
        print("   ⚠️ Pour activer la conversion:")
        print("      1. pip install pydub")
        print("      2. Installer ffmpeg: https://ffmpeg.org/download.html")
    
    print("\n✅ TESTS TERMINÉS !")
    print(f"\n📁 Fichiers audio dans: {service.config.AUDIO_OUTPUT_DIR}")


if __name__ == "__main__":
    test_tts_service()