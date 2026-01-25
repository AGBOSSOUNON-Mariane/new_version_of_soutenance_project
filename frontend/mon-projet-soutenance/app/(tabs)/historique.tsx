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
import { UserService } from '../../services/userService';

export default function HistoriqueScreen() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [userId, setUserId] = useState<string>('anonymous');

  // 🔥 Charger l'ID utilisateur au démarrage
  useEffect(() => {
    initializeUser();
  }, []);

  const initializeUser = async () => {
    try {
      const id = await UserService.getOrCreateUserId();
      setUserId(id);
      console.log('📱 Historique initialisé pour:', id);
      await loadHistory(id);
    } catch (error) {
      console.error('❌ Erreur initialisation utilisateur:', error);
      setLoading(false);
    }
  };

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
              await loadHistory();
              Alert.alert('Succès', 'Historique effacé avec succès');
            } catch (error: any) {
              Alert.alert('Erreur', error.message);
            }
          },
        },
      ]
    );
  };

  const openConversation = (item: HistoryItem) => {
    Alert.alert(
      item.query,
      item.response.substring(0, 200) + '...',
      [
        { text: 'Fermer', style: 'cancel' },
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

        {/* 🔥 SUPPRIMÉ : Section statistiques */}

        {/* Section de nettoyage */}
        {history.length > 0 && (
          <View style={styles.cleanupSection}>
            <TouchableOpacity style={styles.clearButton} onPress={clearHistory}>
              <Ionicons name="trash-outline" size={20} color={Colors.secondary} />
              <Text style={styles.clearButtonText}>Effacer l'historique</Text>
            </TouchableOpacity>
            
            {/* 🔥 SUPPRIMÉ : Bouton de debug */}
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
  timestamp: {
    fontSize: 11,
    color: Colors.gray,
    marginTop: 2,
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
  },
  clearButtonText: {
    fontSize: 16,
    color: Colors.secondary,
    fontWeight: '600',
    marginLeft: 8,
  },
});