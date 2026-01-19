"""
Visualisation des résultats d'évaluation
Génère des graphiques pour la soutenance
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, Any
import numpy as np


class ResultsVisualizer:
    """
    Visualiseur de résultats d'évaluation
    Génère des graphiques professionnels pour la soutenance
    """
    
    def __init__(self, results_path: str, output_dir: str = "figures"):
        """
        Initialise le visualiseur
        
        Args:
            results_path: Chemin vers le fichier JSON de résultats
            output_dir: Dossier pour sauvegarder les figures
        """
        
        with open(results_path, 'r', encoding='utf-8') as f:
            self.results = json.load(f)
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configuration style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 11
        
        print(f"✅ Visualiseur initialisé")
        print(f"   Figures sauvegardées dans: {self.output_dir}")
    
    def plot_all(self):
        """Génère toutes les visualisations"""
        
        print("\n🎨 Génération des visualisations...")
        
        self.plot_metrics_overview()
        self.plot_intent_accuracy()
        self.plot_rag_confusion_matrix()
        self.plot_intent_confusion_matrix()
        self.plot_ragas_metrics()
        self.plot_combined_comparison()
        
        print(f"\n✅ Toutes les figures ont été générées dans {self.output_dir}")
    
    def plot_metrics_overview(self):
        """Vue d'ensemble de toutes les métriques"""
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Récupérer les métriques
        custom = self.results["custom_metrics"]
        ragas = self.results.get("ragas_metrics", {})
        
        metrics = {
            "Intent\nAccuracy": custom["intent_detection"]["overall"],
            "RAG\nAccuracy": custom["rag_activation"]["accuracy"],
            "RAG\nPrecision": custom["rag_activation"]["precision"],
            "RAG\nRecall": custom["rag_activation"]["recall"],
        }
        
        # Ajouter RAGAS si disponible
        if ragas and "error" not in ragas:
            metrics.update({
                "Context\nPrecision": ragas.get("context_precision", 0),
                "Faithfulness": ragas.get("faithfulness", 0),
                "Answer\nRelevancy": ragas.get("answer_relevancy", 0)
            })
        
        # Créer le graphique
        labels = list(metrics.keys())
        values = list(metrics.values())
        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(labels)))
        
        bars = ax.bar(labels, values, color=colors, alpha=0.8, edgecolor='black')
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2., height,
                f'{height:.2%}',
                ha='center', va='bottom', fontweight='bold'
            )
        
        ax.set_ylim(0, 1.1)
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_title('Vue d\'ensemble des métriques d\'évaluation - Agent', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.axhline(y=0.8, color='red', linestyle='--', alpha=0.5, label='Seuil 80%')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "01_metrics_overview.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Vue d'ensemble générée")
    
    def plot_intent_accuracy(self):
        """Accuracy de détection d'intention par type"""
        
        intent_data = self.results["custom_metrics"]["intent_detection"]
        by_intent = intent_data.get("by_intent", {})
        
        if not by_intent:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Traduire les intents en français
        intent_labels = {
            "greeting": "Salutation",
            "thanks": "Remerciement",
            "farewell": "Au revoir",
            "small_talk": "Discussion",
            "off_topic": "Hors-sujet",
            "heritage_question": "Question\npatrimoniale"
        }
        
        labels = [intent_labels.get(k, k) for k in by_intent.keys()]
        values = list(by_intent.values())
        
        colors = ['#2ecc71' if v >= 0.9 else '#f39c12' if v >= 0.7 else '#e74c3c' 
                  for v in values]
        
        bars = ax.bar(labels, values, color=colors, alpha=0.8, edgecolor='black')
        
        # Valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2., height,
                f'{height:.1%}',
                ha='center', va='bottom', fontweight='bold'
            )
        
        ax.set_ylim(0, 1.1)
        ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
        ax.set_title('Précision de détection d\'intention par type', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.axhline(y=intent_data["overall"], color='blue', linestyle='--', 
                   alpha=0.7, label=f'Overall: {intent_data["overall"]:.1%}')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "02_intent_accuracy.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Accuracy par intention générée")
    
    def plot_rag_confusion_matrix(self):
        """Matrice de confusion pour la décision RAG"""
        
        cm_data = self.results["custom_metrics"]["rag_activation"]["confusion_matrix"]
        
        # Créer matrice 2x2
        matrix = np.array([
            [cm_data["tn"], cm_data["fp"]],
            [cm_data["fn"], cm_data["tp"]]
        ])
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        sns.heatmap(
            matrix, 
            annot=True, 
            fmt='d', 
            cmap='Blues',
            xticklabels=['RAG non nécessaire', 'RAG nécessaire'],
            yticklabels=['RAG non activé', 'RAG activé'],
            cbar_kws={'label': 'Nombre de cas'},
            ax=ax,
            annot_kws={'size': 14, 'weight': 'bold'}
        )
        
        ax.set_title('Matrice de confusion - Décision d\'activation RAG', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Vérité terrain (attendu)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Prédiction (agent)', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "03_rag_confusion_matrix.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Matrice de confusion RAG générée")
    
    def plot_intent_confusion_matrix(self):
        """Matrice de confusion pour les intentions"""
        
        cm_dict = self.results["custom_metrics"]["intent_detection"].get("confusion_matrix", {})
        
        if not cm_dict:
            return
        
        # Obtenir toutes les intentions uniques
        all_intents = sorted(set(list(cm_dict.keys()) + 
                                [k for v in cm_dict.values() for k in v.keys()]))
        
        # Créer matrice
        n = len(all_intents)
        matrix = np.zeros((n, n))
        
        for i, expected in enumerate(all_intents):
            for j, detected in enumerate(all_intents):
                matrix[i, j] = cm_dict.get(expected, {}).get(detected, 0)
        
        # Labels français
        intent_labels = {
            "greeting": "Salutation",
            "thanks": "Remerciement",
            "farewell": "Au revoir",
            "small_talk": "Discussion",
            "off_topic": "Hors-sujet",
            "heritage_question": "Question patrimoniale"
        }
        
        labels = [intent_labels.get(i, i) for i in all_intents]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        sns.heatmap(
            matrix,
            annot=True,
            fmt='g',
            cmap='YlOrRd',
            xticklabels=labels,
            yticklabels=labels,
            cbar_kws={'label': 'Nombre de cas'},
            ax=ax
        )
        
        ax.set_title('Matrice de confusion - Détection d\'intention', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Intention détectée', fontsize=12, fontweight='bold')
        ax.set_ylabel('Intention attendue', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "04_intent_confusion_matrix.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Matrice de confusion intentions générée")
    
    def plot_ragas_metrics(self):
        """Graphique radar pour les métriques RAGAS"""
        
        ragas = self.results.get("ragas_metrics", {})
        
        if not ragas or "error" in ragas:
            print("  ⚠️  Pas de métriques RAGAS à visualiser")
            return
        
        # Données
        categories = ['Context\nPrecision', 'Faithfulness', 'Answer\nRelevancy']
        values = [
            ragas.get("context_precision", 0),
            ragas.get("faithfulness", 0),
            ragas.get("answer_relevancy", 0)
        ]
        
        # Nombre de variables
        N = len(categories)
        
        # Angles pour chaque axe
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        values += values[:1]  # Fermer le radar
        angles += angles[:1]
        
        # Plot
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, values, 'o-', linewidth=2, color='#3498db', label='Agent')
        ax.fill(angles, values, alpha=0.25, color='#3498db')
        
        # Labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=12)
        
        # Limites
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], size=10)
        
        ax.set_title('Métriques RAGAS - Qualité du système RAG', 
                     size=14, fontweight='bold', pad=20)
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "05_ragas_radar.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Graphique radar RAGAS généré")
    
    def plot_combined_comparison(self):
        """Comparaison globale des performances"""
        
        custom = self.results["custom_metrics"]
        ragas = self.results.get("ragas_metrics", {})
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Graphique 1: Métriques Agent (custom)
        agent_metrics = {
            'Intent\nDetection': custom["intent_detection"]["overall"],
            'RAG\nActivation': custom["rag_activation"]["accuracy"],
            'RAG\nPrecision': custom["rag_activation"]["precision"],
            'RAG\nRecall': custom["rag_activation"]["recall"]
        }
        
        ax1.barh(list(agent_metrics.keys()), list(agent_metrics.values()), 
                 color='#3498db', alpha=0.8, edgecolor='black')
        
        for i, (k, v) in enumerate(agent_metrics.items()):
            ax1.text(v + 0.02, i, f'{v:.1%}', va='center', fontweight='bold')
        
        ax1.set_xlim(0, 1.1)
        ax1.set_xlabel('Score', fontweight='bold')
        ax1.set_title('Métriques de l\'Agent', fontweight='bold', fontsize=12)
        ax1.axvline(x=0.8, color='red', linestyle='--', alpha=0.5)
        
        # Graphique 2: Métriques RAG (RAGAS)
        if ragas and "error" not in ragas:
            rag_metrics = {
                'Context\nPrecision': ragas.get("context_precision", 0),
                'Faithfulness': ragas.get("faithfulness", 0),
                'Answer\nRelevancy': ragas.get("answer_relevancy", 0)
            }
            
            ax2.barh(list(rag_metrics.keys()), list(rag_metrics.values()), 
                     color='#2ecc71', alpha=0.8, edgecolor='black')
            
            for i, (k, v) in enumerate(rag_metrics.items()):
                ax2.text(v + 0.02, i, f'{v:.3f}', va='center', fontweight='bold')
            
            ax2.set_xlim(0, 1.1)
            ax2.set_xlabel('Score', fontweight='bold')
            ax2.set_title('Métriques du système RAG (RAGAS)', fontweight='bold', fontsize=12)
            ax2.axvline(x=0.8, color='red', linestyle='--', alpha=0.5)
        else:
            ax2.text(0.5, 0.5, 'Métriques RAGAS\nnon disponibles', 
                     ha='center', va='center', fontsize=14)
            ax2.set_xlim(0, 1)
            ax2.set_ylim(0, 1)
            ax2.axis('off')
        
        plt.suptitle('Performance globale de l\'agent', 
                     fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        plt.savefig(self.output_dir / "06_combined_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Comparaison globale générée")
    
    def generate_latex_table(self):
        """Génère un tableau LaTeX pour le mémoire"""
        
        custom = self.results["custom_metrics"]
        ragas = self.results.get("ragas_metrics", {})
        
        latex = r"""
\begin{table}[h]
\centering
\caption{Résultats de l'évaluation de l'agent conversationnel}
\label{tab:evaluation_results}
\begin{tabular}{|l|c|c|}
\hline
\textbf{Métrique} & \textbf{Score} & \textbf{Interprétation} \\
\hline
\multicolumn{3}{|c|}{\textit{Métriques de l'agent (custom)}} \\
\hline
"""
        
        # Métriques custom
        latex += f"Intent Detection Accuracy & {custom['intent_detection']['overall']:.2%} & "
        latex += ("Excellente" if custom['intent_detection']['overall'] >= 0.9 else "Bonne") + r" \\" + "\n"
        
        latex += f"RAG Activation Accuracy & {custom['rag_activation']['accuracy']:.2%} & "
        latex += ("Excellente" if custom['rag_activation']['accuracy'] >= 0.9 else "Bonne") + r" \\" + "\n"
        
        latex += f"RAG Precision & {custom['rag_activation']['precision']:.2%} & "
        latex += ("Excellente" if custom['rag_activation']['precision'] >= 0.9 else "Bonne") + r" \\" + "\n"
        
        latex += f"RAG Recall & {custom['rag_activation']['recall']:.2%} & "
        latex += ("Excellente" if custom['rag_activation']['recall'] >= 0.9 else "Bonne") + r" \\" + "\n"
        
        # RAGAS
        if ragas and "error" not in ragas:
            latex += r"\hline" + "\n"
            latex += r"\multicolumn{3}{|c|}{\textit{Métriques du système RAG (RAGAS)}} \\" + "\n"
            latex += r"\hline" + "\n"
            
            latex += f"Context Precision & {ragas['context_precision']:.4f} & "
            latex += ("Excellente" if ragas['context_precision'] >= 0.8 else "Bonne") + r" \\" + "\n"
            
            latex += f"Faithfulness & {ragas['faithfulness']:.4f} & "
            latex += ("Peu d'hallucinations" if ragas['faithfulness'] >= 0.9 else "Acceptable") + r" \\" + "\n"
            
            latex += f"Answer Relevancy & {ragas['answer_relevancy']:.4f} & "
            latex += ("Réponses pertinentes" if ragas['answer_relevancy'] >= 0.8 else "Acceptable") + r" \\" + "\n"
        
        latex += r"""\hline
\end{tabular}
\end{table}
"""
        
        # Sauvegarder
        latex_path = self.output_dir / "evaluation_table.tex"
        with open(latex_path, 'w', encoding='utf-8') as f:
            f.write(latex)
        
        print(f"  ✅ Tableau LaTeX généré: {latex_path}")


def main():
    """Point d'entrée pour générer les visualisations"""
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python results_visualizer.py <chemin_vers_results.json>")
        print("\nExemple:")
        print("  python results_visualizer.py results/evaluation_results_20250116_143052.json")
        return
    
    results_path = sys.argv[1]
    
    if not Path(results_path).exists():
        print(f"❌ Fichier non trouvé: {results_path}")
        return
    
    visualizer = ResultsVisualizer(results_path)
    visualizer.plot_all()
    visualizer.generate_latex_table()
    
    print("\n✅ Visualisations terminées!")


if __name__ == "__main__":
    main()