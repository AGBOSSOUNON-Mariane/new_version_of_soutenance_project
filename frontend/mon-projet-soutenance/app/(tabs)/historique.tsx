import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Header } from '../../components/common/Header';
import { Colors } from '../../constants/Colors';
import { HistoryService, HistoryItem } from '../../services/historyService';
import { UserService } from '../../services/userService'; // 🔥 NOUVEAU

export default function HistoriqueScreen() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [userId, setUserId] = useState<string>('anonymous'); // 🔥 MODIFIÉ
  const [stats, setStats] = useState({
    totalConversations: 0,
    sitesVisited: new Set<string>(),
    avgConfidence: 0,
    totalTime: 0,
  });

  // 🔥 NOUVEAU : Charger l'ID utilisateur au démarrage
  useEffect(() => {
    initializeUser();
  }, []);

  // 🔥 NOUVEAU : Fonction d'initialisation
  const initializeUser = async () => {
    try {
      const id = await UserService.getOrCreateUserId();
      setUserId(id);
      console.log('📱 Historique initialisé pour:', id);
      await loadHistory(id); // Charger avec le bon ID
    } catch (error) {
      console.error('❌ Erreur initialisation utilisateur:', error);
      setLoading(false);
    }
  };

  // Calculer les statistiques
  useEffect(() => {
    if (history.length > 0) {
      const sites = new Set(
        history
          .map(item => {
            try {
              const metadata = JSON.parse(item.metadata);
              return metadata.sites_covered || [];
            } catch {
              return [];
            }
          })
          .flat()
      );

      const avgConf = history.reduce((sum, item) => sum + item.confidence, 0) / history.length;
      const totalTime = history.reduce((sum, item) => sum + item.processing_time, 0);

      setStats({
        totalConversations: history.length,
        sitesVisited: sites,
        avgConfidence: avgConf,
        totalTime: totalTime,
      });
    }
  }, [history]);

  // 🔥 MODIFIÉ : Accepte userId en paramètre
  const loadHistory = async (userIdToLoad?: string) => {
    const idToUse = userIdToLoad || userId;
    
    try {
      setLoading(true);
      console.log('📊 Chargement historique pour:', idToUse);
      const response = await HistoryService.getUserHistory(idToUse, 50, 0, false);
      setHistory(response.conversations);
      console.log('✅ Historique chargé:', response.conversations.length, 'conversations');
    } catch (error: any) {
      console.error('❌ Erreur chargement historique:', error);
      Alert.alert(
        'Erreur',
        'Impossible de charger l\'historique. Vérifiez que le backend est lancé.'
      );
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const clearHistory = () => {
    Alert.alert(
      'Effacer l\'historique',
      'Êtes-vous sûr de vouloir effacer tout votre historique ? Cette action est irréversible.',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Effacer',
          style: 'destructive',
          onPress: async () => {
            try {
              await HistoryService.clearUserHistory(userId);
              await loadHistory(); // Recharger (vide)
              Alert.alert('Succès', 'Historique effacé avec succès');
            } catch (error: any) {
              Alert.alert('Erreur', error.message);
            }
          },
        },
      ]
    );
  };

  // 🔥 NOUVEAU : Fonction de debug (optionnel)
  const showDebugInfo = async () => {
    const debugInfo = await UserService.getDebugInfo();
    Alert.alert(
      'Informations de debug',
      `ID utilisateur: ${debugInfo.userId}\nProfil: ${debugInfo.profile}\nConversations: ${history.length}`,
      [{ text: 'OK' }]
    );
  };

  const openConversation = (item: HistoryItem) => {
    Alert.alert(
      item.query,
      item.response.substring(0, 200) + '...',
      [
        { text: 'Fermer', style: 'cancel' },
        {
          text: 'Voir dans le chat',
          onPress: () => {
            Alert.alert('Info', 'Navigation bientôt disponible');
          },
        },
      ]
    );
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}min`;
  };

  // Grouper par date
  const groupedHistory = HistoryService.groupByDate(history);

  if (loading) {
    return (
      <View style={styles.container}>
        <Header title="Historique" subtitle="Vos dernières activités" />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Chargement de l'historique...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Header title="Historique" subtitle="Vos dernières activités" />

      <ScrollView
        style={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
          />
        }
      >
        {history.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="time-outline" size={80} color={Colors.lightGray} />
            <Text style={styles.emptyTitle}>Aucun historique</Text>
            <Text style={styles.emptySubtitle}>
              Vos conversations avec l'assistant apparaîtront ici
            </Text>
            {/* 🔥 NOUVEAU : Bouton de debug optionnel (peut être retiré en prod) */}
            <TouchableOpacity 
              style={styles.debugButton} 
              onPress={showDebugInfo}
            >
              <Text style={styles.debugButtonText}>ℹ️ Infos technique</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.historyContainer}>
            {/* Historique groupé par date */}
            {Array.from(groupedHistory.entries()).map(([dateLabel, items]) => (
              <View key={dateLabel}>
                <Text style={styles.dateHeader}>{dateLabel}</Text>
                {items.map((item) => (
                  <TouchableOpacity
                    key={item.id}
                    style={styles.historyCard}
                    onPress={() => openConversation(item)}
                  >
                    <View style={styles.historyContent}>
                      {/* Icône selon le type */}
                      <View style={styles.iconContainer}>
                        <Text style={styles.iconEmoji}>
                          {HistoryService.getConversationIcon(item.response_type)}
                        </Text>
                      </View>

                      {/* Informations */}
                      <View style={styles.historyInfo}>
                        <Text style={styles.historyTitle} numberOfLines={1}>
                          {HistoryService.getQuerySummary(item.query, 40)}
                        </Text>
                        <Text style={styles.historySubtitle} numberOfLines={2}>
                          {item.response.substring(0, 80)}...
                        </Text>

                        {/* Métadonnées */}
                        <View style={styles.metadataRow}>
                          {/* Confiance */}
                          <View style={styles.metadataItem}>
                            <View
                              style={[
                                styles.confidenceDot,
                                {
                                  backgroundColor: HistoryService.getConfidenceColor(
                                    item.confidence
                                  ),
                                },
                              ]}
                            />
                            <Text style={styles.metadataText}>
                              {(item.confidence * 100).toFixed(0)}%
                            </Text>
                          </View>

                          {/* Images */}
                          {item.images_count > 0 && (
                            <View style={styles.metadataItem}>
                              <Ionicons name="images-outline" size={12} color={Colors.gray} />
                              <Text style={styles.metadataText}>{item.images_count}</Text>
                            </View>
                          )}

                          {/* Sources */}
                          {item.sources_count > 0 && (
                            <View style={styles.metadataItem}>
                              <Ionicons name="book-outline" size={12} color={Colors.gray} />
                              <Text style={styles.metadataText}>{item.sources_count}</Text>
                            </View>
                          )}

                          {/* Temps */}
                          <View style={styles.metadataItem}>
                            <Ionicons name="time-outline" size={12} color={Colors.gray} />
                            <Text style={styles.metadataText}>
                              {formatTime(item.processing_time)}
                            </Text>
                          </View>
                        </View>

                        {/* Timestamp */}
                        <Text style={styles.timestamp}>
                          {HistoryService.formatTime(item.timestamp)}
                        </Text>
                      </View>

                      {/* Badge profil */}
                      <View style={styles.profileBadge}>
                        <Text style={styles.profileBadgeText}>
                          {item.user_profile === 'touriste' ? '🧳' : 
                           item.user_profile === 'étudiant' ? '🎓' : 
                           item.user_profile === 'élève' ? '📚' : '👤'}
                        </Text>
                      </View>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            ))}

            {/* Bouton pour charger plus */}
            {history.length >= 50 && (
              <TouchableOpacity style={styles.loadMoreButton} onPress={() => loadHistory()}>
                <Text style={styles.loadMoreText}>Charger plus</Text>
                <Ionicons name="chevron-down-outline" size={20} color={Colors.primary} />
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Section statistiques */}
        {history.length > 0 && (
          <View style={styles.statsSection}>
            <Text style={styles.statsTitle}>Vos statistiques</Text>

            <View style={styles.statsGrid}>
              <View style={styles.statCard}>
                <Ionicons name="chatbubbles" size={24} color={Colors.primary} />
                <Text style={styles.statNumber}>{stats.totalConversations}</Text>
                <Text style={styles.statLabel}>Conversations</Text>
              </View>

              <View style={styles.statCard}>
                <Ionicons name="location" size={24} color={Colors.primary} />
                <Text style={styles.statNumber}>{stats.sitesVisited.size}</Text>
                <Text style={styles.statLabel}>Sites visités</Text>
              </View>

              <View style={styles.statCard}>
                <Ionicons name="speedometer" size={24} color={Colors.primary} />
                <Text style={styles.statNumber}>
                  {(stats.avgConfidence * 100).toFixed(0)}%
                </Text>
                <Text style={styles.statLabel}>Confiance moy.</Text>
              </View>

              <View style={styles.statCard}>
                <Ionicons name="time" size={24} color={Colors.primary} />
                <Text style={styles.statNumber}>{formatTime(stats.totalTime)}</Text>
                <Text style={styles.statLabel}>Temps total</Text>
              </View>
            </View>
          </View>
        )}

        {/* Section de nettoyage */}
        {history.length > 0 && (
          <View style={styles.cleanupSection}>
            <TouchableOpacity style={styles.clearButton} onPress={clearHistory}>
              <Ionicons name="trash-outline" size={20} color={Colors.secondary} />
              <Text style={styles.clearButtonText}>Effacer l'historique</Text>
            </TouchableOpacity>
            
            {/* 🔥 NOUVEAU : Bouton de debug (optionnel) */}
            <TouchableOpacity 
              style={styles.debugButton} 
              onPress={showDebugInfo}
            >
              <Text style={styles.debugButtonText}>ℹ️ Infos technique</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 15,
    fontSize: 16,
    color: Colors.gray,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 40,
    paddingVertical: 100,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginTop: 20,
    marginBottom: 10,
  },
  emptySubtitle: {
    fontSize: 16,
    color: Colors.gray,
    textAlign: 'center',
    lineHeight: 24,
  },
  historyContainer: {
    paddingHorizontal: 20,
    paddingTop: 20,
  },
  dateHeader: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.gray,
    textTransform: 'uppercase',
    marginBottom: 12,
    marginTop: 10,
    letterSpacing: 0.5,
  },
  historyCard: {
    backgroundColor: Colors.white,
    borderRadius: 15,
    marginBottom: 12,
    padding: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  historyContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  iconContainer: {
    width: 50,
    height: 50,
    borderRadius: 12,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  iconEmoji: {
    fontSize: 24,
  },
  historyInfo: {
    flex: 1,
  },
  historyTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.textDark,
    marginBottom: 5,
  },
  historySubtitle: {
    fontSize: 13,
    color: Colors.gray,
    lineHeight: 18,
    marginBottom: 8,
  },
  metadataRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 6,
  },
  metadataItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metadataText: {
    fontSize: 11,
    color: Colors.gray,
    fontWeight: '500',
  },
  confidenceDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  timestamp: {
    fontSize: 11,
    color: Colors.gray,
    marginTop: 2,
  },
  profileBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  profileBadgeText: {
    fontSize: 16,
  },
  loadMoreButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    marginTop: 10,
    marginBottom: 20,
  },
  loadMoreText: {
    fontSize: 16,
    color: Colors.primary,
    fontWeight: '600',
    marginRight: 5,
  },
  statsSection: {
    marginTop: 20,
    paddingHorizontal: 20,
  },
  statsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 15,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 15,
    justifyContent: 'space-between',
  },
  statCard: {
    backgroundColor: Colors.white,
    borderRadius: 15,
    padding: 20,
    alignItems: 'center',
    width: '47%',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginTop: 10,
    marginBottom: 5,
  },
  statLabel: {
    fontSize: 12,
    color: Colors.gray,
    textAlign: 'center',
  },
  cleanupSection: {
    paddingHorizontal: 20,
    paddingVertical: 30,
    alignItems: 'center',
  },
  clearButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
    borderWidth: 1,
    borderColor: Colors.secondary,
    marginBottom: 10, // 🔥 NOUVEAU
  },
  clearButtonText: {
    fontSize: 16,
    color: Colors.secondary,
    fontWeight: '600',
    marginLeft: 8,
  },
  // 🔥 NOUVEAUX STYLES
  debugButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: Colors.lightGray,
    marginTop: 10,
  },
  debugButtonText: {
    fontSize: 14,
    color: Colors.gray,
  },
});