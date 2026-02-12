import React from 'react';
import { Text, StyleProp, TextStyle } from 'react-native';

interface FormattedTextProps {
  children: string;
  style?: StyleProp<TextStyle>;
}

export const FormattedText: React.FC<FormattedTextProps> = ({ children, style }) => {
  // Regex pour capturer **texte** ET "texte"
  const parts = children.split(/(\*\*.*?\*\*|"[^"]+?")/g);
  
  return (
    <Text style={style}>
      {parts.map((part, index) => {
        // Gras avec **
        if (part.startsWith('**') && part.endsWith('**')) {
          const boldText = part.slice(2, -2);
          return (
            <Text key={index} style={{ fontWeight: 'bold' }}>
              {boldText}
            </Text>
          );
        }
        
        // Gras avec guillemets "texte"
        if (part.startsWith('"') && part.endsWith('"')) {
          const quotedText = part.slice(1, -1);
          return (
            <Text key={index} style={{ fontWeight: 'bold' }}>
              {quotedText}
            </Text>
          );
        }
        
        return <Text key={index}>{part}</Text>;
      })}
    </Text>
  );
};