/**
 * Types pour l'API Adjä avec TTS
 * Correspond à api_with_tts.py
 */

// ============================================================================
// REQUÊTES
// ============================================================================

export interface ChatRequest {
  message: string;                 // ← Message de l'utilisateur
  session_id?: string;             // ← Session (optionnel)
  language?: string | null;        // ← null = auto-détection
  generate_audio?: boolean;        // ← Générer l'audio ?
  verbose?: boolean;               // ← Debug
}

// ============================================================================
// RÉPONSES
// ============================================================================

export interface ChatResponse {
  success: boolean;
  session_id: string;
  query: string;
  response: string;                // ← Texte de la réponse
  images: string[];                // ← Liste d'URLs/chemins d'images
  sources: string[];               // ← Liste de sources
  used_rag: boolean;
  intent: string;
  language: string;
  chunks_used?: number;
  timestamp: string;
  
  // 🆕 CHAMPS AUDIO
  audio_available: boolean;
  audio_url?: string;
  audio_filename?: string;
  audio_duration_seconds?: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  services: {
    pinecone: string;
    gemini: string;
    tts: string;
    audio_storage?: string;
  };
  active_sessions: number;
  audio_files_count?: number;
}