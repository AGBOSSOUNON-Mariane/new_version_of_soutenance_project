import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Link } from 'expo-router';
import { Header } from '../../components/common/Header';
import { Colors } from '../../constants/Colors';
import { sites } from '../../data/sites';

const { width } = Dimensions.get('window');

export default function HomeScreen() {
  // Fonction pour mapper les noms de sites vers leurs routes
  const getSiteRoute = (siteName: string): string => {
    const routes: { [key: string]: string } = {
      'Abomey': 'abomey',
      'Porto-Novo': 'portonovo',
      'Ganvié': 'ganvie',
      'Ouidah': 'ouidah'
    };
    return routes[siteName] || 'ouidah';
  };

  return (
    <View style={styles.container}>
      <Header 
        title="Récits, rois et monuments du Bénin" 
        subtitle="Explorez l'héritage vivant de 4 grands pôles culturels"
      />
      
      

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Section Sites culturels */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Sites culturels</Text>
            <View style={styles.sitesCount}>
              <Text style={styles.sitesCountText}>4 sites culturels</Text>
            </View>
          </View>

          {/* Liste des sites */}
          <View style={styles.sitesContainer}>
            {sites.map((site, index) => (
              <View key={site.id} style={styles.siteCard}>
                <Image 
                  source={site.image} 
                  style={styles.siteImage}
                  defaultSource={require('../../assets/images/placeholder.jpg')}
                />
                
                {/* Badge populaire */}
                {site.isPopular && (
                  <View style={styles.popularBadge}>
                    <Text style={styles.popularText}>Populaire</Text>
                  </View>
                )}
                
                {/* Bouton favoris */}
                <TouchableOpacity style={styles.favoriteButton}>
                  <Ionicons 
                    name={site.isFavorite ? "heart" : "heart-outline"} 
                    size={24} 
                    color={site.isFavorite ? Colors.heart : Colors.white} 
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
                    <View style={styles.stat}>
                      <Ionicons name="camera-outline" size={16} color={Colors.gray} />
                      <Text style={styles.statText}>Photos</Text>
                    </View>
                  </View>
                  
                  <View style={styles.tags}>
                    {site.tags.map((tag, tagIndex) => (
                      <View key={tagIndex} style={styles.tag}>
                        <Text style={styles.tagText}>{tag}</Text>
                      </View>
                    ))}
                  </View>

                  {/* UTILISATION DE LA FONCTION getSiteRoute */}
                  <Link href={`../details/${getSiteRoute(site.name)}`} asChild>
                    <TouchableOpacity style={styles.exploreButton}>
                     <Text style={styles.exploreButtonText}>Explorer</Text>
                    </TouchableOpacity>
                  </Link>
                </View>
              </View>
            ))}
          </View>
        </View>

        {/* Section Assistant IA */}
        <Link href="./assistant" asChild>
          <TouchableOpacity style={styles.assistantCard} activeOpacity={1}>
            <LinearGradient
              colors={[Colors.primary, Colors.secondary]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.assistantGradient}
            >
              <Ionicons name="chatbubbles" size={40} color={Colors.white} />
              <Text style={styles.assistantTitle}>Besoin d'aide ?</Text>
              <Text style={styles.assistantSubtitle}>
                Notre assistant IA vous guide dans votre découverte
              </Text>
              <View style={styles.startConversationButton}>
                <Ionicons name="chatbubbles" size={20} color={Colors.primary} />
                <Text style={styles.startConversationText}>Commencer la conversation</Text>
              </View>
            </LinearGradient>
          </TouchableOpacity>
        </Link>
      </ScrollView>
    </View>
  );
}

// Vos styles restent identiques
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  quickButtons: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 15,
    gap: 15,
  },
  quickButton: {
    flex: 1,
    backgroundColor: Colors.primary + '80',
    borderRadius: 15,
    padding: 15,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 70,
  },
  quickButtonText: {
    color: Colors.white,
    fontSize: 12,
    fontWeight: '600',
    marginTop: 5,
  },
  content: {
    flex: 1,
  },
  section: {
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: Colors.textDark,
  },
  sitesCount: {
    backgroundColor: Colors.primary + '20',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
  },
  sitesCountText: {
    color: Colors.primary,
    fontSize: 12,
    fontWeight: '600',
  },
  sitesContainer: {
    gap: 20,
  },
  siteCard: {
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
  popularBadge: {
    position: 'absolute',
    top: 15,
    left: 15,
    backgroundColor: Colors.secondary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  popularText: {
    color: Colors.white,
    fontSize: 12,
    fontWeight: 'bold',
  },
  favoriteButton: {
    position: 'absolute',
    top: 15,
    right: 15,
    backgroundColor: 'rgba(0,0,0,0.3)',
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
    marginBottom: 15,
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
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 15,
  },
  tag: {
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 8,
  },
  tagText: {
    color: Colors.primary,
    fontSize: 12,
    fontWeight: '500',
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
  assistantCard: {
    marginHorizontal: 20,
    marginVertical: 20,
    borderRadius: 20,
    overflow: 'hidden',
  },
  assistantGradient: {
    padding: 30,
    alignItems: 'center',
  },
  assistantTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: Colors.white,
    marginTop: 15,
    marginBottom: 10,
  },
  assistantSubtitle: {
    fontSize: 16,
    color: Colors.white,
    textAlign: 'center',
    opacity: 0.9,
    marginBottom: 20,
  },
  startConversationButton: {
    backgroundColor: Colors.white,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
  },
  startConversationText: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
});