/**
 * Service de gestion d'identité utilisateur
 * Génère et persiste un ID unique par appareil
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

export class UserService {
  private static USER_ID_KEY = '@benin_heritage:user_id';
  private static USER_PROFILE_KEY = '@benin_heritage:user_profile';

  /**
   * Récupère ou crée un ID utilisateur unique
   * L'ID est généré une seule fois et persisté localement
   */
  static async getOrCreateUserId(): Promise<string> {
    try {
      // Vérifier si on a déjà un ID
      let userId = await AsyncStorage.getItem(this.USER_ID_KEY);
      
      if (!userId) {
        // Créer un nouvel ID unique basé sur timestamp + random
        const timestamp = Date.now();
        const random = Math.random().toString(36).substr(2, 9);
        userId = `user_${timestamp}_${random}`;
        
        // Sauvegarder pour les prochaines fois
        await AsyncStorage.setItem(this.USER_ID_KEY, userId);
        
        console.log('🆕 Nouvel utilisateur créé:', userId);
      } else {
        console.log('👤 Utilisateur existant:', userId);
      }
      
      return userId;
      
    } catch (error) {
      console.error('❌ Erreur UserService.getOrCreateUserId:', error);
      // Fallback si AsyncStorage échoue
      return `anonymous_${Date.now()}`;
    }
  }

  /**
   * Récupère l'ID utilisateur actuel (sans en créer un nouveau)
   */
  static async getUserId(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(this.USER_ID_KEY);
    } catch (error) {
      console.error('❌ Erreur UserService.getUserId:', error);
      return null;
    }
  }

  /**
   * Définir le profil utilisateur (touriste, étudiant, élève)
   */
  static async setUserProfile(profile: 'touriste' | 'étudiant' | 'élève'): Promise<void> {
    try {
      await AsyncStorage.setItem(this.USER_PROFILE_KEY, profile);
      console.log('✅ Profil utilisateur sauvegardé:', profile);
    } catch (error) {
      console.error('❌ Erreur UserService.setUserProfile:', error);
    }
  }

  /**
   * Récupérer le profil utilisateur
   */
  static async getUserProfile(): Promise<string> {
    try {
      const profile = await AsyncStorage.getItem(this.USER_PROFILE_KEY);
      return profile || 'touriste'; // Défaut
    } catch (error) {
      console.error('❌ Erreur UserService.getUserProfile:', error);
      return 'touriste';
    }
  }

  /**
   * Réinitialiser l'ID utilisateur (utile pour les tests)
   * ATTENTION : Efface l'historique côté client
   */
  static async resetUserId(): Promise<void> {
    try {
      await AsyncStorage.removeItem(this.USER_ID_KEY);
      await AsyncStorage.removeItem(this.USER_PROFILE_KEY);
      console.log('🔄 ID utilisateur réinitialisé');
    } catch (error) {
      console.error('❌ Erreur UserService.resetUserId:', error);
    }
  }

  /**
   * Obtenir des infos de debug
   */
  static async getDebugInfo(): Promise<{userId: string | null, profile: string}> {
    const userId = await this.getUserId();
    const profile = await this.getUserProfile();
    return { userId, profile };
  }
}