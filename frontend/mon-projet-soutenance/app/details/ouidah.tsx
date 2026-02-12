import React from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Image,
  ImageBackground,
  StatusBar,
  Dimensions,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { Link, useRouter } from "expo-router";
import { Colors } from "../../constants/Colors";

const { width, height } = Dimensions.get("window");

export default function OuidahDetailsScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* 🆕 Boutons header FIXES en haut (en dehors du ScrollView) */}
      <View style={styles.fixedHeader}>
        <View style={styles.headerButtons}>
          <TouchableOpacity
            style={styles.headerButton}
            onPress={() => router.back()}
          >
            <Ionicons name="arrow-back" size={24} color={Colors.white} />
          </TouchableOpacity>

          
        </View>
      </View>

      {/* 🔧 ScrollView qui contient TOUT (y compris l'image) */}
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        bounces={true}
      >
        {/* 🔧 Image DANS le ScrollView */}
        <ImageBackground
          source={require("../../assets/images/ouidah.jpg")}
          style={styles.headerImage}
          resizeMode="cover"
        >
          {/* Overlay sombre */}
          <LinearGradient
            colors={["rgba(0,0,0,0.3)", "rgba(0,0,0,0.7)"]}
            style={styles.overlay}
          >
            {/* Informations du site */}
            <View style={styles.siteHeaderInfo}>
              <Text style={styles.siteName}>Ouidah</Text>

              <View style={styles.siteStats}>
                <View style={styles.statItem}>
                  <Ionicons name="star" size={16} color={Colors.star} />
                  <Text style={styles.statText}>4.7</Text>
                </View>

                <View style={styles.statItem}>
                  <Ionicons name="people" size={16} color={Colors.white} />
                  <Text style={styles.statText}>1.8k</Text>
                </View>

                <View style={styles.statItem}>
                  <Ionicons name="time" size={16} color={Colors.white} />
                  <Text style={styles.statText}>4h</Text>
                </View>
              </View>
            </View>
          </LinearGradient>
        </ImageBackground>

        {/* Contenu qui scroll */}
        <View style={styles.content}>
          {/* Description */}
          <View style={styles.section}>
            <Text style={styles.description}>
              Ouidah est une ville côtière chargée d'histoire, connue comme le
              berceau du vaudou et un important port de la traite négrière.
              Aujourd'hui, c'est un lieu de pèlerinage spirituel et de mémoire
              historique.
            </Text>

            {/* Tags - si vous voulez les garder */}
            {/* <View style={styles.tags}>
              <View style={styles.tag}>
                <Text style={styles.tagText}>Historique</Text>
              </View>
              <View style={styles.tag}>
                <Text style={styles.tagText}>Spirituel</Text>
              </View>
              <View style={styles.tag}>
                <Text style={styles.tagText}>Culturel</Text>
              </View>
            </View> */}
          </View>

          {/* Points d'intérêt */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Points d'intérêt</Text>

            <View style={styles.interestPoints}>
              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Temple des Pythons</Text>
              </View>

              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Route des Esclaves</Text>
              </View>

              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Porte du Non-Retour</Text>
              </View>

              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Forêt sacrée de Kpassè</Text>
              </View>
            </View>
          </View>

          {/* Assistant IA Call-to-action */}
          <View style={styles.section}>
            <View style={styles.assistantCard}>
              <LinearGradient
                colors={[Colors.primary, Colors.secondary]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.assistantGradient}
              >
                <Ionicons name="chatbubbles" size={32} color={Colors.white} />
                <Text style={styles.assistantTitle}>
                  Questions sur Ouidah ?
                </Text>
                <Text style={styles.assistantSubtitle}>
                  Notre assistant IA peut vous en dire plus
                </Text>

                <Link href={{ pathname: "../assistant", params: { pole: "Ouidah" } }} asChild>
                  <TouchableOpacity style={styles.askButton}>
                    <Text style={styles.askButtonText}>Poser une question</Text>
                  </TouchableOpacity>
                </Link>
              </LinearGradient>
            </View>
          </View>

          {/* Espacement pour la barre d'onglets */}
          <View style={styles.bottomSpacing} />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  // 🆕 Header fixe au-dessus du ScrollView
  fixedHeader: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 10,
    paddingTop: 50,
    paddingHorizontal: 20,
  },
  headerButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  rightButtons: {
    flexDirection: "row",
    gap: 10,
  },
  headerButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(0,0,0,0.4)", // 🔧 Plus sombre pour mieux voir
    alignItems: "center",
    justifyContent: "center",
  },
  // 🆕 ScrollView
  scrollView: {
    flex: 1,
  },
  headerImage: {
    width: width,
    height: height * 0.5,
  },
  overlay: {
    flex: 1,
    justifyContent: "flex-end", // 🔧 Informations en bas
  },
  siteHeaderInfo: {
    paddingHorizontal: 20,
    paddingBottom: 30,
  },
  siteName: {
    fontSize: 48,
    fontWeight: "bold",
    color: Colors.white,
    marginBottom: 15,
  },
  siteStats: {
    flexDirection: "row",
    gap: 20,
  },
  statItem: {
    flexDirection: "row",
    alignItems: "center",
  },
  statText: {
    color: Colors.white,
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 5,
  },
  content: {
    backgroundColor: Colors.background,
  },
  section: {
    padding: 20,
  },
  description: {
    fontSize: 16,
    lineHeight: 24,
    color: Colors.textDark,
    marginBottom: 20,
  },
  tags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
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
    fontSize: 14,
    fontWeight: "500",
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: Colors.textDark,
    marginBottom: 20,
  },
  interestPoints: {
    gap: 15,
  },
  interestPoint: {
    flexDirection: "row",
    alignItems: "center",
  },
  pointDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.primary,
    marginRight: 15,
  },
  pointText: {
    fontSize: 16,
    color: Colors.textDark,
  },
  assistantCard: {
    borderRadius: 20,
    overflow: "hidden",
  },
  assistantGradient: {
    padding: 25,
    alignItems: "center",
  },
  assistantTitle: {
    fontSize: 20,
    fontWeight: "bold",
    color: Colors.white,
    marginTop: 10,
    marginBottom: 5,
  },
  assistantSubtitle: {
    fontSize: 14,
    color: Colors.white,
    opacity: 0.9,
    textAlign: "center",
    marginBottom: 20,
  },
  askButton: {
    backgroundColor: Colors.white,
    paddingHorizontal: 25,
    paddingVertical: 12,
    borderRadius: 25,
  },
  askButtonText: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: "bold",
  },
  bottomSpacing: {
    height: 100,
  },
});
