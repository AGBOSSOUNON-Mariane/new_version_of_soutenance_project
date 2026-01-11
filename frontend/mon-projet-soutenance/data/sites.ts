export interface Site {
  id: string;
  name: string;
  description: string;
  rating: number;
  visitors: string;
  duration: string;
  image: any; // Pour require() des images locales
  tags: string[];
  isPopular?: boolean;
  isFavorite?: boolean;
}

export const sites: Site[] = [
  {
    id: '1',
    name: 'Abomey',
    description: 'Palais royaux historiques',
    rating: 4.8,
    visitors: '2.1k',
    duration: '2h30',
    image: require('../assets/images/abomey.jpg'), // Vous devrez ajouter ces images
    tags: ['Histoire', 'Patrimoine'],
    isPopular: true,
  },
  {
    id: '2',
    name: 'Porto-Novo',
    description: 'La grande mosquée de Porto Novo',
    rating: 4.6,
    visitors: '1.5k',
    duration: '3h',
    image: require('../assets/images/portonovo.jpg'),
    tags: ['Architecture', 'Capitale'],
  },
  {
    id: '3',
    name: 'Ganvié',
    description: 'Village lacustre sur pilotis',
    rating: 4.9,
    visitors: '3.1k',
    duration: '2h',
    image: require('../assets/images/ganvie.jpg'),
    tags: ['Nature', 'Village'],
    isFavorite: true,
  },
  {
    id: '4',
    name: 'Ouidah',
    description: 'La Porte de Non-Retour',
    rating: 4.7,
    visitors: '1.8k',
    duration: '2h45',
    image: require('../assets/images/ouidah.jpg'),
    tags: ['Histoire', 'Mémoire'],
  },
];

export interface HistoryItem {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  timestamp: string;
  type: 'visit' | 'chat';
  image?: any;
}

export const historyItems: HistoryItem[] = [
  {
    id: '1',
    title: 'Ganvié - Village lacustre',
    subtitle: 'Consultation complète du site',
    description: 'Village lacustre sur pilotis',
    timestamp: "Aujourd'hui, 14:30",
    type: 'visit',
    image: require('../assets/images/ganvie.jpg'),
  },
  {
    id: '2',
    title: "Conversation avec l'assistant IA",
    subtitle: "Questions sur l'histoire d'Abomey",
    description: 'Discussion sur les palais royaux',
    timestamp: 'Hier, 16:45',
    type: 'chat',
  },
];