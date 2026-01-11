import api from './api';

export interface HistoryItem {
  id: string;
  user_id: string;
  session_id: string;
  query: string;
  response: string;
  user_profile: string;
  language: string;
  confidence: number;
  processing_time: number;
  response_type: string;
  images_count: number;
  sources_count: number;
  metadata: string;
  timestamp: string;
}

export interface UserHistory {
  user_id: string;
  conversations: HistoryItem[];
  count: number;
  limit: number;
  offset: number;
  includes_tts: boolean;
}

export interface SessionHistory {
  user_id: string;
  session_id: string;
  conversations: HistoryItem[];
  count: number;
}

export class HistoryService {
  
  /**
   * Récupérer l'historique d'un utilisateur
   */
  static async getUserHistory(
    userId: string, 
    limit: number = 50, 
    offset: number = 0,
    includeTts: boolean = false
  ): Promise<UserHistory> {
    try {
      const response = await api.get<UserHistory>('/history/' + userId, {
        params: { limit, offset, include_tts: includeTts }
      });
      return response.data;
    } catch (error: any) {
      console.error('❌ Erreur getUserHistory:', error);
      throw new Error(
        error.response?.data?.detail || 
        'Impossible de charger l\'historique'
      );
    }
  }

  /**
   * Récupérer l'historique d'une session spécifique
   */
  static async getSessionHistory(
    userId: string,
    sessionId: string
  ): Promise<SessionHistory> {
    try {
      const response = await api.get<SessionHistory>(
        `/session/${userId}/${sessionId}`
      );
      return response.data;
    } catch (error: any) {
      console.error('❌ Erreur getSessionHistory:', error);
      throw new Error(
        error.response?.data?.detail || 
        'Impossible de charger la session'
      );
    }
  }

  /**
   * Formater une date de façon lisible
   */
  static formatDate(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "À l'instant";
    if (diffMins < 60) return `Il y a ${diffMins} min`;
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    if (diffDays === 1) return "Hier";
    if (diffDays < 7) return `Il y a ${diffDays} jours`;
    
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  }

  /**
   * Formater l'heure
   */
  static formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Grouper les conversations par date
   */
  static groupByDate(conversations: HistoryItem[]): Map<string, HistoryItem[]> {
    const grouped = new Map<string, HistoryItem[]>();
    
    conversations.forEach(conv => {
      const dateKey = this.formatDate(conv.timestamp);
      if (!grouped.has(dateKey)) {
        grouped.set(dateKey, []);
      }
      grouped.get(dateKey)!.push(conv);
    });
    
    return grouped;
  }

  /**
   * Obtenir un résumé de la requête (premiers mots)
   */
  static getQuerySummary(query: string, maxLength: number = 50): string {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  }

  /**
   * Obtenir l'icône selon le type de conversation
   */
  static getConversationIcon(responseType: string): string {
    switch (responseType) {
      case 'success': return '✅';
      case 'off_topic': return '❓';
      case 'error': return '❌';
      default: return '💬';
    }
  }

  /**
   * Obtenir la couleur selon le niveau de confiance
   */
  static getConfidenceColor(confidence: number): string {
    if (confidence >= 0.7) return '#27ae60'; // Vert
    if (confidence >= 0.5) return '#f39c12'; // Orange
    return '#e74c3c'; // Rouge
  }
}