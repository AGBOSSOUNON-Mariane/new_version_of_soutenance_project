import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Header } from '../../components/common/Header';
import { Colors } from '../../constants/Colors';
import { sites } from '../../data/sites';

export default function FavorisScreen() {
  const [favoritesSites, setFavoritesSites] = useState(
    sites.filter(site => site.isFavorite)
  );

  const toggleFavorite = (siteId: string) => {
    setFavoritesSites(prev => 
      prev.map(site => 
        site.id === siteId 
          ? { ...site, isFavorite: !site.isFavorite }
          : site
      ).filter(site => site.isFavorite)
    );
  };

  return (
    <View style={styles.container}>
      <Header 
        title="Mes Favoris" 
        subtitle={`${favoritesSites.length} site${favoritesSites.length > 1 ? 's' : ''} sauvegardé${favoritesSites.length > 1 ? 's' : ''}`}
      />
      
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {favoritesSites.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="heart-outline" size={80} color={Colors.lightGray} />
            <Text style={styles.emptyTitle}>Aucun favori</Text>
            <Text style={styles.emptySubtitle}>
              Ajoutez des sites à vos favoris pour les retrouver facilement
            </Text>
          </View>
        ) : (
          <View style={styles.favoritesContainer}>
            {favoritesSites.map((site) => (
              <View key={site.id} style={styles.favoriteCard}>
                <Image source={site.image} style={styles.siteImage} />
                
                {/* Bouton de suppression des favoris */}
                <TouchableOpacity 
                  style={styles.favoriteButton}
                  onPress={() => toggleFavorite(site.id)}
                >
                  <Ionicons 
                    name="heart" 
                    size={24} 
                    color={Colors.heart} 
                  />
                </TouchableOpacity>
                
                {/* Rating */}
                <View style={styles.rating}>
                  <Ionicons name="star" size={16} color={Colors.star} />
                  <Text style={styles.ratingText}>{site.rating}</Text>
                </View>
                
                {/* Informations du site */}
                <View style={styles.siteInfo}>
                  <Text style={styles.siteName}>{site.name}</Text>
                  <Text style={styles.siteDescription}>{site.description}</Text>
                  
                  <View style={styles.siteStats}>
                    <View style={styles.stat}>
                      <Ionicons name="people-outline" size={16} color={Colors.gray} />
                      <Text style={styles.statText}>{site.visitors}</Text>
                    </View>
                    <View style={styles.stat}>
                      <Ionicons name="time-outline" size={16} color={Colors.gray} />
                      <Text style={styles.statText}>{site.duration}</Text>
                    </View>
                  </View>
                  
                  <Text style={styles.addedText}>Ajouté il y a 2 jours</Text>
                  
                  <TouchableOpacity style={styles.exploreButton}>
                    <Text style={styles.exploreButtonText}>Explorer</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </View>
        )}
        
        {/* Suggestions de sites à ajouter */}
        {favoritesSites.length > 0 && (
          <View style={styles.suggestionsSection}>
            <Text style={styles.suggestionsTitle}>Vous pourriez aussi aimer</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <View style={styles.suggestionsContainer}>
                {sites.filter(site => !site.isFavorite).map((site) => (
                  <TouchableOpacity key={site.id} style={styles.suggestionCard}>
                    <Image source={site.image} style={styles.suggestionImage} />
                    <View style={styles.suggestionOverlay}>
                      <TouchableOpacity style={styles.addFavoriteButton}>
                        <Ionicons name="heart-outline" size={20} color={Colors.white} />
                      </TouchableOpacity>
                    </View>
                    <View style={styles.suggestionInfo}>
                      <Text style={styles.suggestionName}>{site.name}</Text>
                      <View style={styles.suggestionRating}>
                        <Ionicons name="star" size={14} color={Colors.star} />
                        <Text style={styles.suggestionRatingText}>{site.rating}</Text>
                      </View>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
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
  favoritesContainer: {
    paddingHorizontal: 20,
    paddingTop: 20,
    gap: 20,
  },
  favoriteCard: {
    backgroundColor: Colors.white,
    borderRadius: 20,
    overflow: 'hidden',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  siteImage: {
    width: '100%',
    height: 200,
    backgroundColor: Colors.lightGray,
  },
  favoriteButton: {
    position: 'absolute',
    top: 15,
    right: 15,
    backgroundColor: 'rgba(255,255,255,0.9)',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rating: {
    position: 'absolute',
    top: 15,
    left: 15,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
  },
  ratingText: {
    marginLeft: 4,
    fontSize: 14,
    fontWeight: 'bold',
    color: Colors.textDark,
  },
  siteInfo: {
    padding: 20,
  },
  siteName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 5,
  },
  siteDescription: {
    fontSize: 16,
    color: Colors.textLight,
    marginBottom: 15,
  },
  siteStats: {
    flexDirection: 'row',
    marginBottom: 10,
    gap: 20,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statText: {
    marginLeft: 5,
    fontSize: 14,
    color: Colors.gray,
  },
  addedText: {
    fontSize: 12,
    color: Colors.gray,
    marginBottom: 15,
    fontStyle: 'italic',
  },
  exploreButton: {
    backgroundColor: Colors.primary,
    borderRadius: 25,
    paddingVertical: 12,
    alignItems: 'center',
  },
  exploreButtonText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: 'bold',
  },
  suggestionsSection: {
    marginTop: 30,
    paddingBottom: 20,
  },
  suggestionsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 15,
    paddingHorizontal: 20,
  },
  suggestionsContainer: {
    flexDirection: 'row',
    paddingLeft: 20,
    gap: 15,
  },
  suggestionCard: {
    width: 150,
    backgroundColor: Colors.white,
    borderRadius: 15,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  suggestionImage: {
    width: '100%',
    height: 100,
    backgroundColor: Colors.lightGray,
  },
  suggestionOverlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    padding: 10,
  },
  addFavoriteButton: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  suggestionInfo: {
    padding: 12,
  },
  suggestionName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 5,
  },
  suggestionRating: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  suggestionRatingText: {
    marginLeft: 3,
    fontSize: 12,
    fontWeight: 'bold',
    color: Colors.textDark,
  },
});