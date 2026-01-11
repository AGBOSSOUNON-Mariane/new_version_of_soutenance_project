import React, { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  Image,
  Dimensions,
  Keyboard,
  Pressable,
  Linking, // 🆕 Import pour ouvrir les liens
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Audio } from "expo-av";
import { Header } from "../../components/common/Header";
import { Colors } from "../../constants/Colors";
import { ChatService } from "../../services/chatService";

const { width } = Dimensions.get("window");
const IMAGE_SIZE = (width - 60) / 3;

interface Message {
  id: string;
  text: string;
  sender: "user" | "assistant";
  timestamp: string;
  images?: string[];
  sources?: string[];
  isLoading?: boolean;
  hasAudio?: boolean;
  audioUrl?: string;
  audioDuration?: number;
}

const quickQuestions = [
  "Qui est le roi Ghézo ?",
  "Parle-moi des Amazones",
  "Parle moi de Porto-Novo",
  "Histoire de Ganvié",
];

export default function AssistantScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Bonjour ! Je suis Adjä, ta guide culturelle virtuelle. Que souhaites-tu savoir sur le patrimoine béninois ?",
      sender: "assistant",
      timestamp: new Date().toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    },
  ]);

  const [inputText, setInputText] = useState("");
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  const [keyboardVisible, setKeyboardVisible] = useState(false); // 🆕 Ajouter cette ligne
  const inputRef = useRef<TextInput>(null); // 🆕 Ajouter cette ligne

  useEffect(() => {
    checkApiConnection();

    Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
    });

    // 🆕 Écouter le clavier
    const keyboardDidShowListener = Keyboard.addListener(
      "keyboardDidShow",
      () => {
        setKeyboardVisible(true);
        setTimeout(() => {
          scrollViewRef.current?.scrollToEnd({ animated: true });
        }, 100);
      }
    );

    const keyboardDidHideListener = Keyboard.addListener(
      "keyboardDidHide",
      () => {
        setKeyboardVisible(false);
      }
    );

    return () => {
      if (sound) {
        sound.unloadAsync();
      }
      keyboardDidShowListener.remove();
      keyboardDidHideListener.remove();
    };
  }, []);

  useEffect(() => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [messages.length]);

  const checkApiConnection = async () => {
    try {
      const isOk = await ChatService.testConnection();
      setIsConnected(isOk);

      if (!isOk) {
        Alert.alert(
          "⚠️ Connexion API",
          "Impossible de contacter le serveur. Vérifie que ton backend est lancé."
        );
      }
    } catch (error) {
      setIsConnected(false);
      console.error("❌ Test connexion:", error);
    }
  };

  const playAudio = async (audioUrl: string, messageId: string) => {
    console.log("▶️ playAudio appelé:", { audioUrl, messageId });

    try {
      if (sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
        setPlayingMessageId(null);
      }

      console.log("🔊 Lecture:", audioUrl);

      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        { shouldPlay: true }
      );

      setSound(newSound);
      setPlayingMessageId(messageId);

      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setPlayingMessageId(null);
        }
      });
    } catch (error) {
      console.error("❌ Erreur audio:", error);
      Alert.alert("Erreur", "Impossible de lire l'audio");
    }
  };

  const stopAudio = async () => {
    console.log("⏸️ stopAudio appelé");

    if (sound) {
      await sound.stopAsync();
      await sound.unloadAsync();
      setSound(null);
      setPlayingMessageId(null);
    }
  };

  const getImageName = (imagePath: string): string => {
    // Ex: "Donnees_soutenance\Abomey\...\palais du roi Ghézo.jpg"
    const parts = imagePath.split(/[\\\/]/); // Split par \ ou /
    const filename = parts[parts.length - 1]; // Dernier élément

    // Enlever l'extension (.jpg, .jpeg, .png, etc.)
    let name = filename.replace(/\.(jpg|jpeg|png|gif|webp)$/i, "");

    // Remplacer TOUS les underscores par des espaces
    name = name.replace(/_/g, " ");

    // Simplifications supplémentaires
    name = name
      .replace(/^image des /i, "") // Enlever "image des" au début
      .replace(/^une image des /i, "") // Enlever "une image des"
      .replace(/^la /i, "") // Enlever "la" au début
      .replace(/extraite du film/gi, "-") // Remplacer "extraite du film" par "-"
      .replace(/érigée à/gi, "à") // Simplifier "érigée à"
      .replace(/\s+/g, " ") // Enlever espaces multiples
      .trim();

    // Capitaliser la première lettre
    if (name.length > 0) {
      name = name.charAt(0).toUpperCase() + name.slice(1);
    }

    // Limiter la longueur pour éviter débordement
    if (name.length > 40) {
      name = name.substring(0, 37) + "...";
    }

    return name;
  };

  // 🆕 Fonction pour extraire le nom du fichier depuis le chemin
  //const getImageName = (imagePath: string): string => {
  // Ex: "Donnees_soutenance\Abomey\...\palais du roi Ghézo.jpg"
  // Retourne: "palais du roi Ghézo"
  //const parts = imagePath.split(/[\\\/]/); // Split par \ ou /
  //const filename = parts[parts.length - 1]; // Dernier élément
  //return filename.replace(/\.(jpg|jpeg|png|gif|webp)$/i, ''); // Enlever l'extension
  //};

  // 🆕 Fonction pour ouvrir un lien
  const openLink = async (url: string) => {
    try {
      const supported = await Linking.canOpenURL(url);

      if (supported) {
        await Linking.openURL(url);
      } else {
        Alert.alert("Erreur", `Impossible d'ouvrir ce lien : ${url}`);
      }
    } catch (error) {
      console.error("❌ Erreur ouverture lien:", error);
      Alert.alert("Erreur", "Impossible d'ouvrir le lien");
    }
  };

  // 🆕 Fonction pour extraire le titre et l'URL d'une source
  const parseSource = (source: string): { title: string; url?: string } => {
    // Format attendu: "Wikipédia (FR) — Ghézo, https://fr.wikipedia.org/..."
    const match = source.match(/(.*?),\s*(https?:\/\/[^\s]+)/);

    if (match) {
      return {
        title: match[1].trim(),
        url: match[2].trim(),
      };
    }

    // Si pas de lien, retourner juste le texte
    return { title: source };
  };

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    if (isConnected === false) {
      Alert.alert("❌ Pas de connexion", "Le serveur n'est pas accessible.", [
        { text: "Réessayer", onPress: checkApiConnection },
        { text: "Annuler", style: "cancel" },
      ]);
      return;
    }

    Keyboard.dismiss();

    const userMessage: Message = {
      id: Date.now().toString(),
      text: text.trim(),
      sender: "user",
      timestamp: new Date().toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");

    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: "🤔 Adjä réfléchit...",
      sender: "assistant",
      timestamp: "",
      isLoading: true,
    };

    setMessages((prev) => [...prev, loadingMessage]);

    try {
      const response = await ChatService.sendMessage(text.trim(), true);

      setMessages((prev) => prev.filter((msg) => msg.id !== loadingMessage.id));

      const audioUrlFinal = response.audio_url
        ? ChatService.getAudioUrl(response.audio_url)
        : undefined;

      const assistantMessage: Message = {
        id: (Date.now() + 2).toString(),
        text: response.response,
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        images:
          response.images && response.images.length > 0
            ? response.images
            : undefined,
        sources:
          response.sources && response.sources.length > 0
            ? response.sources
            : undefined,
        hasAudio: response.audio_available,
        audioUrl: audioUrlFinal,
        audioDuration: response.audio_duration_seconds,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      setMessages((prev) => prev.filter((msg) => msg.id !== loadingMessage.id));

      const errorMessage: Message = {
        id: (Date.now() + 3).toString(),
        text: `❌ Erreur : ${error.message}`,
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      setMessages((prev) => [...prev, errorMessage]);
      console.error("❌ Erreur:", error);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      <Header
        title="Assistant Adjä"
        subtitle={isConnected ? "✅ En ligne" : "❌ Hors ligne"}
      />

      {isConnected === false && (
        <View style={styles.connectionBanner}>
          <Ionicons name="warning-outline" size={20} color={Colors.white} />
          <Text style={styles.connectionText}>Backend non connecté</Text>
          <TouchableOpacity onPress={checkApiConnection}>
            <Ionicons name="refresh-outline" size={20} color={Colors.white} />
          </TouchableOpacity>
        </View>
      )}

      <ScrollView
        ref={scrollViewRef}
        style={styles.messagesContainer}
        contentContainerStyle={[
          styles.messagesContent,
          keyboardVisible && { paddingBottom: 300 }, // 🆕
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled" // 🆕
      >
        {messages.map((message) => (
          <View
            key={message.id}
            style={[
              styles.messageContainer,
              message.sender === "user"
                ? styles.userMessage
                : styles.assistantMessage,
            ]}
          >
            <View
              style={[
                styles.messageBubble,
                message.sender === "user"
                  ? styles.userBubble
                  : styles.assistantBubble,
              ]}
            >
              <Text
                style={[
                  styles.messageText,
                  message.sender === "user"
                    ? styles.userText
                    : styles.assistantText,
                ]}
              >
                {message.text}
              </Text>

              {message.isLoading && (
                <ActivityIndicator
                  size="small"
                  color={Colors.primary}
                  style={styles.loadingIndicator}
                />
              )}

              {/* 🔧 IMAGES AVEC NOM */}
              {message.images && message.images.length > 0 && (
                <View style={styles.imagesContainer}>
                  <Text style={styles.sectionTitle}>
                    📸 Images ({message.images.length})
                  </Text>
                  <View style={styles.imagesGrid}>
                    {message.images.slice(0, 6).map((img, index) => (
                      <View key={index} style={styles.imageWrapper}>
                        <Image
                          source={{ uri: ChatService.getImageUrl(img) }}
                          style={styles.image}
                          resizeMode="cover"
                        />
                        {/* 🆕 NOM DE L'IMAGE */}
                        <Text style={styles.imageName} numberOfLines={2}>
                          {getImageName(img)}
                        </Text>
                      </View>
                    ))}
                  </View>
                  {message.images.length > 6 && (
                    <Text style={styles.moreText}>
                      +{message.images.length - 6} autres
                    </Text>
                  )}
                </View>
              )}

              {/* 🔧 SOURCES CLIQUABLES */}
              {message.sources && message.sources.length > 0 && (
                <View style={styles.sourcesContainer}>
                  <Text style={styles.sectionTitle}>📚 Sources :</Text>
                  {message.sources.map((source, index) => {
                    const { title, url } = parseSource(source);

                    return (
                      <TouchableOpacity
                        key={index}
                        style={styles.sourceItem}
                        onPress={() => url && openLink(url)}
                        disabled={!url}
                      >
                        <Ionicons
                          name="link-outline"
                          size={14}
                          color={url ? Colors.primary : Colors.gray}
                        />
                        <Text
                          style={[
                            styles.sourceText,
                            url && styles.sourceTextClickable,
                          ]}
                          numberOfLines={2}
                        >
                          {title}
                        </Text>
                        {url && (
                          <Ionicons
                            name="open-outline"
                            size={12}
                            color={Colors.primary}
                          />
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              )}

              {/* BOUTON AUDIO */}
              {message.hasAudio && message.audioUrl && (
                <Pressable
                  style={({ pressed }) => [
                    styles.audioButton,
                    pressed && styles.audioButtonPressed,
                  ]}
                  onPress={(e) => {
                    e?.stopPropagation?.();
                    console.log("🔊 CLIC sur bouton audio !");

                    if (playingMessageId === message.id) {
                      stopAudio();
                    } else {
                      playAudio(message.audioUrl!, message.id);
                    }
                  }}
                  hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                  <Ionicons
                    name={
                      playingMessageId === message.id
                        ? "pause-circle"
                        : "play-circle"
                    }
                    size={24}
                    color={Colors.primary}
                  />
                  <Text style={styles.audioText}>
                    {playingMessageId === message.id
                      ? "En lecture..."
                      : "Écouter"}
                  </Text>
                  {message.audioDuration && (
                    <Text style={styles.audioDuration}>
                      {Math.round(message.audioDuration)}s
                    </Text>
                  )}
                </Pressable>
              )}
            </View>

            {!message.isLoading && (
              <Text style={styles.timestamp}>{message.timestamp}</Text>
            )}
          </View>
        ))}

        {messages.length === 1 && (
          <View style={styles.quickQuestionsContainer}>
            <Text style={styles.quickQuestionsTitle}>
              💡 Questions rapides :
            </Text>
            <View style={styles.quickQuestions}>
              {quickQuestions.map((question, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.quickQuestion}
                  onPress={() => sendMessage(question)}
                >
                  <Text style={styles.quickQuestionText}>{question}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      </ScrollView>

      <View style={styles.inputContainer}>
        <TextInput
          ref={inputRef} // 🆕
          style={styles.textInput}
          placeholder="Pose ta question..."
          placeholderTextColor={Colors.gray}
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={500}
          editable={isConnected !== false}
          onFocus={() => {// 🆕
            setTimeout(() => {
              scrollViewRef.current?.scrollToEnd({ animated: true });
            }, 300);
          }}
          onSubmitEditing={() => {
            if (inputText.trim()) {
              sendMessage(inputText);
            }
          }}
        />

        <TouchableOpacity
          style={[
            styles.sendButton,
            inputText.trim() &&
              isConnected !== false &&
              styles.sendButtonActive,
          ]}
          onPress={() => sendMessage(inputText)}
          disabled={!inputText.trim() || isConnected === false}
        >
          <Ionicons
            name="send"
            size={20}
            color={
              inputText.trim() && isConnected !== false
                ? Colors.white
                : Colors.gray
            }
          />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  connectionBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#e74c3c",
    paddingHorizontal: 15,
    paddingVertical: 10,
    gap: 10,
  },
  connectionText: {
    flex: 1,
    color: Colors.white,
    fontSize: 12,
    fontWeight: "500",
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
  },
  messageContainer: {
    marginBottom: 15,
  },
  userMessage: {
    alignItems: "flex-end",
  },
  assistantMessage: {
    alignItems: "flex-start",
  },
  messageBubble: {
    maxWidth: "85%",
    paddingHorizontal: 15,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userBubble: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: 5,
  },
  assistantBubble: {
    backgroundColor: Colors.white,
    borderBottomLeftRadius: 5,
    elevation: 1,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: Colors.white,
  },
  assistantText: {
    color: Colors.textDark,
  },
  timestamp: {
    fontSize: 12,
    color: Colors.gray,
    marginTop: 5,
    marginHorizontal: 15,
  },
  loadingIndicator: {
    marginTop: 10,
  },
  imagesContainer: {
    marginTop: 15,
    paddingTop: 15,
    borderTopWidth: 1,
    borderTopColor: Colors.lightGray,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: Colors.textDark,
    marginBottom: 10,
  },
  imagesGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  // 🆕 Wrapper pour image + nom
  imageWrapper: {
    width: IMAGE_SIZE,
  },
  image: {
    width: IMAGE_SIZE,
    height: IMAGE_SIZE,
    borderRadius: 8,
    backgroundColor: Colors.lightGray,
  },
  // 🆕 Nom de l'image
  imageName: {
    fontSize: 10,
    color: Colors.gray,
    marginTop: 4,
    textAlign: "center",
    lineHeight: 12,
  },
  moreText: {
    fontSize: 12,
    color: Colors.gray,
    marginTop: 8,
    fontStyle: "italic",
  },
  sourcesContainer: {
    marginTop: 15,
    paddingTop: 15,
    borderTopWidth: 1,
    borderTopColor: Colors.lightGray,
  },
  // 🆕 Item source cliquable
  sourceItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 8,
    gap: 8,
  },
  sourceText: {
    flex: 1,
    fontSize: 12,
    color: Colors.gray,
    lineHeight: 18,
  },
  // 🆕 Style pour source cliquable
  sourceTextClickable: {
    color: Colors.primary,
    textDecorationLine: "underline",
  },
  audioButton: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
    paddingVertical: 10,
    paddingHorizontal: 15,
    backgroundColor: Colors.background,
    borderRadius: 20,
    gap: 10,
    elevation: 2,
    zIndex: 10,
  },
  audioButtonPressed: {
    opacity: 0.7,
    backgroundColor: "#e8e8e8",
  },
  audioText: {
    flex: 1,
    fontSize: 13,
    color: Colors.primary,
    fontWeight: "600",
  },
  audioDuration: {
    fontSize: 11,
    color: Colors.gray,
  },
  quickQuestionsContainer: {
    marginTop: 20,
    marginBottom: 20,
  },
  quickQuestionsTitle: {
    fontSize: 16,
    color: Colors.gray,
    marginBottom: 15,
  },
  quickQuestions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  quickQuestion: {
    backgroundColor: Colors.white,
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Colors.lightGray,
  },
  quickQuestionText: {
    color: Colors.textDark,
    fontSize: 14,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: 20,
    paddingVertical: 15,
    backgroundColor: Colors.white,
    borderTopWidth: 1,
    borderTopColor: Colors.lightGray,
    gap: 10,
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.lightGray,
    borderRadius: 25,
    paddingHorizontal: 15,
    paddingVertical: 12,
    fontSize: 16,
    color: Colors.textDark,
    maxHeight: 100,
    backgroundColor: Colors.background,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.lightGray,
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonActive: {
    backgroundColor: Colors.primary,
  },
});
