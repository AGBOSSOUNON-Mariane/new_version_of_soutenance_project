import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Image,
  StyleSheet,
  TouchableOpacity,
  Text,
  Dimensions,
  StatusBar,
  Platform,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context'; // 🔥 AJOUT

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface ImageViewerProps {
  visible: boolean;
  images: string[];
  initialIndex: number;
  onClose: () => void;
  getImageUrl: (path: string) => string;
  getImageName: (path: string) => string;
}

export const ImageViewer: React.FC<ImageViewerProps> = ({
  visible,
  images,
  initialIndex,
  onClose,
  getImageUrl,
  getImageName,
}) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const insets = useSafeAreaInsets(); // 🔥 AJOUT

  // ✅ TOUS les hooks doivent être AVANT tout return conditionnel
  useEffect(() => {
    if (visible) {
      setCurrentIndex(initialIndex);
    }
  }, [visible, initialIndex]);

  // ✅ Maintenant on peut retourner null après tous les hooks
  if (!visible || !images || images.length === 0) {
    return null;
  }

  const goToPrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const goToNext = () => {
    if (currentIndex < images.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handleClose = () => {
    setCurrentIndex(initialIndex);
    onClose();
  };

  // Sécurité supplémentaire - vérifier que l'index est dans les limites
  const safeCurrentIndex = Math.min(Math.max(0, currentIndex), images.length - 1);
  const currentImage = images[safeCurrentIndex] || '';

  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="fade"
      onRequestClose={handleClose}
      statusBarTranslucent={true}
    >
      <View style={styles.modalContainer}>
        <StatusBar hidden={true} />
        
        {/* Background overlay - cliquable pour fermer */}
        <TouchableOpacity 
          style={styles.backdrop}
          activeOpacity={1}
          onPress={handleClose}
        />

        {/* Header */}
        <View style={[
          styles.header,
          { top: Math.max(insets.top + 10, 20) } // 🔥 CORRECTION : adaptatif selon le téléphone
        ]}>
          <TouchableOpacity
            style={styles.closeButton}
            onPress={handleClose}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="close" size={30} color="#fff" />
          </TouchableOpacity>

          <View style={styles.headerInfo}>
            <Text style={styles.imageCounter}>
              {safeCurrentIndex + 1} / {images.length}
            </Text>
            <Text style={styles.imageName} numberOfLines={1}>
              {getImageName(currentImage)}
            </Text>
          </View>
        </View>

        {/* Image avec zoom simple */}
        <ScrollView
          contentContainerStyle={styles.imageContainer}
          maximumZoomScale={3}
          minimumZoomScale={1}
          showsHorizontalScrollIndicator={false}
          showsVerticalScrollIndicator={false}
        >
          <Image
            source={{ uri: getImageUrl(currentImage) }}
            style={styles.image}
            resizeMode="contain"
          />
        </ScrollView>

        {/* Navigation arrows */}
        {images.length > 1 && (
          <View style={styles.navigationContainer}>
            <TouchableOpacity
              style={[
                styles.navButton,
                safeCurrentIndex === 0 && styles.navButtonDisabled,
              ]}
              onPress={goToPrevious}
              disabled={safeCurrentIndex === 0}
            >
              <Ionicons
                name="chevron-back"
                size={30}
                color={safeCurrentIndex === 0 ? '#666' : '#fff'}
              />
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.navButton,
                safeCurrentIndex === images.length - 1 && styles.navButtonDisabled,
              ]}
              onPress={goToNext}
              disabled={safeCurrentIndex === images.length - 1}
            >
              <Ionicons
                name="chevron-forward"
                size={30}
                color={safeCurrentIndex === images.length - 1 ? '#666' : '#fff'}
              />
            </TouchableOpacity>
          </View>
        )}

        {/* Bottom instructions */}
        <View style={[
          styles.footer,
          { bottom: Math.max(insets.bottom + 20, 30) } // 🔥 CORRECTION : adaptatif selon le téléphone
        ]}>
          <Text style={styles.instructionText}>
            {images.length > 1 ? 'Utilisez les flèches pour naviguer' : 'Appuyez pour fermer'}
          </Text>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'transparent',
  },
  header: {
    position: 'absolute',
    // 🔥 SUPPRIMÉ : top géré dynamiquement dans le JSX
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    zIndex: 10,
  },
  closeButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerInfo: {
    flex: 1,
    marginLeft: 15,
  },
  imageCounter: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  imageName: {
    fontSize: 14,
    color: '#ccc',
  },
  imageContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
    paddingBottom: 100,
  },
  image: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT * 0.7,
  },
  navigationContainer: {
    position: 'absolute',
    top: '50%',
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    transform: [{ translateY: -25 }],
    zIndex: 10,
  },
  navButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  navButtonDisabled: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  footer: {
    position: 'absolute',
    // 🔥 SUPPRIMÉ : bottom géré dynamiquement dans le JSX
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 10,
  },
  instructionText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
  },
});