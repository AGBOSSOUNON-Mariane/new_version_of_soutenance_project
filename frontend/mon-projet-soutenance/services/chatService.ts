/**
 * Service de communication avec l'API Adjä (avec TTS)
 * Adapté pour api_with_tts.py
 */

import api, { API_BASE_URL } from './api';
import { ChatRequest, ChatResponse, HealthStatus } from '../types/api';
import { UserService } from './userService'; // 🔥 NOUVEAU

export class ChatService {
  
  // Session ID persistante
  private static sessionId: string = `mobile-${Date.now()}`;

  /**
   * 🔥 Envoyer un message à Adjä (avec user_id automatique)
   */
  static async sendMessage(message: string, generateAudio: boolean = true): Promise<ChatResponse> {
    try {
      // 🔥 NOUVEAU : Récupérer l'ID utilisateur
      const userId = await UserService.getOrCreateUserId();
      const userProfile = await UserService.getUserProfile();
      
      const requestBody: ChatRequest = {
        message: message.trim(),
        session_id: this.sessionId,
        user_id: userId,              // 🔥 NOUVEAU
        user_profile: userProfile,    // 🔥 NOUVEAU
        language: null,
        generate_audio: generateAudio,
        verbose: true,
      };
      
      console.log('📤 Envoi à /chat:', {
        message: requestBody.message,
        user_id: userId,
        user_profile: userProfile
      });
      
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
      console.log(error)
      return false;
    }
  }


  /**
   * Obtenir l'URL complète d'un fichier audio
   */
  static getAudioUrl(audioFilename: string): string {
    console.log('🎵 getAudioUrl appelé avec:', audioFilename);
    
    if (audioFilename.startsWith('http://') || audioFilename.startsWith('https://')) {
      const filename = audioFilename.split('/audio/').pop() || audioFilename;
      const finalUrl = `${API_BASE_URL}/audio/${filename}`;
      
      console.log('🎵 URL backend:', audioFilename);
      console.log('🎵 Nom fichier extrait:', filename);
      console.log('🎵 URL finale:', finalUrl);
      
      return finalUrl;
    }
    
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
    
    let cleanPath = imagePath.replace(/\\/g, '/');
    cleanPath = cleanPath.replace(/^Donnees_soutenance\//, '');
    
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