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

export default function AbomeyDetailsScreen() {
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

          <View style={styles.rightButtons}>
            <TouchableOpacity style={styles.headerButton}>
              <Ionicons name="heart-outline" size={24} color={Colors.white} />
            </TouchableOpacity>

            <TouchableOpacity style={styles.headerButton}>
              <Ionicons name="share-outline" size={24} color={Colors.white} />
            </TouchableOpacity>
          </View>
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
          source={require("../../assets/images/abomey.jpg")}
          style={styles.headerImage}
          resizeMode="cover"
        >
          <LinearGradient
            colors={["rgba(0,0,0,0.3)", "rgba(0,0,0,0.7)"]}
            style={styles.overlay}
          >
            {/* Informations du site */}
            <View style={styles.siteHeaderInfo}>
              <Text style={styles.siteName}>Abomey</Text>

              <View style={styles.siteStats}>
                <View style={styles.statItem}>
                  <Ionicons name="star" size={16} color={Colors.star} />
                  <Text style={styles.statText}>4.8</Text>
                </View>

                <View style={styles.statItem}>
                  <Ionicons name="people" size={16} color={Colors.white} />
                  <Text style={styles.statText}>2.3k</Text>
                </View>

                <View style={styles.statItem}>
                  <Ionicons name="time" size={16} color={Colors.white} />
                  <Text style={styles.statText}>3h</Text>
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
              Les palais royaux d'Abomey sont un témoignage exceptionnel de
              l'ancien royaume du Dahomey. Ces palais, construits entre le XVIIe
              et le XIXe siècle, abritent aujourd'hui un musée fascinant qui
              retrace l'histoire de cette puissante civilisation africaine.
            </Text>
          </View>

          {/* Points d'intérêt */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Points d'intérêt</Text>

            <View style={styles.interestPoints}>
              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Palais du roi Ghezo</Text>
              </View>

              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Les amazones du Dahomey</Text>
              </View>

              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Musée historique d'Abomey</Text>
              </View>

              <View style={styles.interestPoint}>
                <View style={styles.pointDot} />
                <Text style={styles.pointText}>Palais royaux d'Abomey</Text>
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
                  Questions sur Abomey ?
                </Text>
                <Text style={styles.assistantSubtitle}>
                  Notre assistant IA peut vous en dire plus
                </Text>

                <Link href="../assistant" asChild>
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
