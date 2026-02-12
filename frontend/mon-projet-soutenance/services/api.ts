import axios from 'axios';

// 🔥 CONFIGURATION IMPORTANTE POUR EXPO
// Quand tu utilises Expo Go sur ton téléphone, tu dois utiliser l'IP de ton PC
// Remplace cette URL par l'IP de ton PC si tu testes sur téléphone physique
// Pour trouver ton IP: 
// - Windows: ipconfig dans cmd
// - Mac/Linux: ifconfig dans terminal

// Pour émulateur Android: http://10.0.2.2:8000
// Pour émulateur iOS: http://localhost:8000
// Pour téléphone physique: http://192.168.X.X:8000 (remplace par ton IP)
// const API_BASE_URL = 'http://54.88.20.85:8000'; // Change ça selon ton cas

const API_BASE_URL = 'http://192.168.1.104:8000'; // Change ça selon ton cas

// Créer une instance axios configurée
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3600000, // 60 minutes (ton agent RAG peut prendre du temps)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour logger les requêtes (utile pour debug)
api.interceptors.request.use(
  (config) => {
    console.log('📤 Requête API:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ Erreur requête:', error);
    return Promise.reject(error);
  }
);

// Intercepteur pour logger les réponses
api.interceptors.response.use(
  (response) => {
    console.log('✅ Réponse API:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('❌ Erreur réponse:', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

export default api;
export { API_BASE_URL };