/**
 * Service de communication avec l'API Adjä (avec TTS)
 * Adapté pour api_with_tts.py
 */

import api, { API_BASE_URL } from './api';
import { ChatRequest, ChatResponse, HealthStatus } from '../types/api';

export class ChatService {
  
  // Session ID persistante
  private static sessionId: string = `mobile-${Date.now()}`;

  /**
   * 🔥 Envoyer un message à Adjä
   */
  static async sendMessage(message: string, generateAudio: boolean = true): Promise<ChatResponse> {
    try {
      const requestBody: ChatRequest = {
        message: message.trim(),
        session_id: this.sessionId,
        language: null,              // Auto-détection
        generate_audio: generateAudio,
        verbose: true,
      };
      
      console.log('📤 Envoi à /chat:', requestBody);
      
      const response = await api.post<ChatResponse>('/chat', requestBody);
      
      console.log('✅ Réponse:', {
        intent: response.data.intent,
        language: response.data.language,
        audio: response.data.audio_available,
      });
      
      return response.data;
      
    } catch (error: any) {
      console.error('❌ Erreur:', error);
      
      let errorMessage = 'Impossible de contacter Adjä';
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      throw new Error(errorMessage);
    }
  }

  /**
   * Vérifier la santé de l'API
   */
  static async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await api.get<HealthStatus>('/health');
      return response.data;
    } catch (error) {
      console.error('❌ Health check:', error);
      throw new Error('API non disponible');
    }
  }

  /**
   * Tester la connexion
   */
  static async testConnection(): Promise<boolean> {
    try {
      const health = await this.checkHealth();
      return health.status === 'healthy';
    } catch (error) {
      return false;
    }
  }

  /**
   * Obtenir l'URL complète d'un fichier audio
   * ✅ CORRIGÉ : Gère les URLs complètes du backend
   */
  static getAudioUrl(audioFilename: string): string {
    console.log('🎵 getAudioUrl appelé avec:', audioFilename);
    
    // Si l'URL est déjà complète, remplacer l'IP du backend par celle de l'app
    if (audioFilename.startsWith('http://') || audioFilename.startsWith('https://')) {
      // Extraire juste le nom du fichier depuis l'URL complète
      // Ex: http://10.229.92.13:8000/audio/99e1706fedcd_fr.mp3 → 99e1706fedcd_fr.mp3
      const filename = audioFilename.split('/audio/').pop() || audioFilename;
      const finalUrl = `${API_BASE_URL}/audio/${filename}`;
      
      console.log('🎵 URL backend:', audioFilename);
      console.log('🎵 Nom fichier extrait:', filename);
      console.log('🎵 URL finale:', finalUrl);
      
      return finalUrl;
    }
    
    // Sinon, construire l'URL normalement
    const finalUrl = `${API_BASE_URL}/audio/${audioFilename}`;
    console.log('🎵 URL construite:', finalUrl);
    return finalUrl;
  }
  
  /**
   * Obtenir l'URL complète d'une image
   */
  static getImageUrl(imagePath: string): string {
    if (imagePath.startsWith('http')) {
      return imagePath;
    }
    
    // Nettoyer le chemin (remplacer \ par /)
    let cleanPath = imagePath.replace(/\\/g, '/');
    
    // 🔥 IMPORTANT : Enlever le préfixe "Donnees_soutenance/"
    cleanPath = cleanPath.replace(/^Donnees_soutenance\//, '');
    
    // Construire l'URL finale
    const finalUrl = `${API_BASE_URL}/images/${cleanPath}`;
    
    console.log('🖼️ Image path:', imagePath);
    console.log('🔗 Final URL:', finalUrl);
    
    return finalUrl;
  }

  /**
   * Réinitialiser la session
   */
  static resetSession(): void {
    this.sessionId = `mobile-${Date.now()}`;
    console.log('🔄 Session réinitialisée');
  }
}