import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants/Colors';
export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.gray,
        tabBarStyle: {
          backgroundColor: Colors.white,
          borderTopWidth: 1,
          borderTopColor: Colors.lightGray,
          height: 60,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Accueil',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons 
              name={focused ? 'location' : 'location-outline'} 
              size={24} 
              color={color} 
            />
          ),
        }}
      />
      <Tabs.Screen
        name="assistant"
        options={{
          title: 'Assistant',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons 
              name={focused ? 'chatbubbles' : 'chatbubbles-outline'} 
              size={24} 
              color={color} 
            />
          ),
        }}
      />
      <Tabs.Screen
        name="favoris"
        options={{
          title: 'Favoris',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons 
              name={focused ? 'heart' : 'heart-outline'} 
              size={24} 
              color={color} 
            />
          ),
        }}
      />
      <Tabs.Screen
        name="historique"
        options={{
          title: 'Historique',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons 
              name={focused ? 'time' : 'time-outline'} 
              size={24} 
              color={color} 
            />
          ),
        }}
      />
    </Tabs>
  );
}