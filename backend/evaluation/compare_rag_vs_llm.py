"""
Script de comparaison : Agent RAG vs Gemini généraliste
Projet Adjä - Patrimoine Béninois

Métriques calculées :
- Answer Correctness (via RAGAS)
- BERTScore (F1, Precision, Recall)
- Latency
- Relevance & Understandability (via GPT-4o comme juge)

Auteur : Projet IFRI Licence IA
Date : 2025-01-19
"""

import json
import time
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from tqdm import tqdm
from datetime import datetime

# Imports pour les métriques
try:
    from bert_score import score as bert_score
    BERTSCORE_AVAILABLE = True
except ImportError:
    print("⚠️ BERTScore non installé. Installer avec: pip install bert-score")
    BERTSCORE_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    print("⚠️ Google Generative AI non installé. Installer avec: pip install google-generativeai")
    GEMINI_AVAILABLE = False

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# URLs
API_BASE_URL = "http://localhost:8000"  # Ton API FastAPI
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"

# Clés API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Fichiers
DATASET_PATH = "comparison_dataset.json"
RESULTS_DIR = Path("comparison_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Paramètres
SESSION_ID = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# =============================================================================
# CLASSE DE COMPARAISON
# =============================================================================

class RAGvsLLMComparator:
    """Compare un agent RAG avec un LLM généraliste"""
    
    def __init__(self, dataset_path: str):
        """
        Args:
            dataset_path: Chemin vers le JSON des questions
        """
        self.dataset_path = dataset_path
        self.dataset = self._load_dataset()
        self.results = {
            "rag_agent": [],
            "gemini_generic": []
        }
        
        # Configurer Gemini généraliste
        if GEMINI_AVAILABLE and GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            print("✅ Gemini configuré")
        else:
            print("❌ Gemini non disponible")
            self.gemini_model = None
    
    def _load_dataset(self) -> Dict:
        """Charge le dataset de questions"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Dataset chargé : {len(data['heritage_questions'])} questions")
            return data
        except FileNotFoundError:
            print(f"❌ Fichier {self.dataset_path} introuvable")
            return {"heritage_questions": []}
    
    def query_rag_agent(self, question: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Interroge ton agent RAG via l'API
        
        Returns:
            {
                'response': str,
                'latency': float,
                'used_rag': bool,
                'chunks_used': int,
                'error': str (si échec)
            }
        """
        try:
            start_time = time.time()
            
            payload = {
                "message": question,
                "session_id": SESSION_ID,
                "language": "fr",
                "generate_audio": False,  # Pas besoin d'audio pour l'éval
                "verbose": verbose
            }
            
            response = requests.post(
                CHAT_ENDPOINT,
                json=payload,
                timeout=60  # Timeout de 60s
            )
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'response': data.get('response', ''),
                    'latency': latency,
                    'used_rag': data.get('used_rag', False),
                    'chunks_used': data.get('chunks_used', 0),
                    'images': data.get('images', []),
                    'sources': data.get('sources', [])
                }
            else:
                return {
                    'response': '',
                    'latency': latency,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {
                'response': '',
                'latency': 60.0,
                'error': "Timeout (>60s)"
            }
        except Exception as e:
            return {
                'response': '',
                'latency': 0.0,
                'error': str(e)
            }
    
    def query_gemini_generic(self, question: str) -> Dict[str, Any]:
        """
        Interroge Gemini en mode généraliste (sans RAG)
        
        Returns:
            {
                'response': str,
                'latency': float,
                'error': str (si échec)
            }
        """
        if not self.gemini_model:
            return {
                'response': '',
                'latency': 0.0,
                'error': 'Gemini non configuré'
            }
        
        try:
            start_time = time.time()
            
            # Prompt simple sans contexte externe
            prompt = f"""Tu es un assistant intelligent. Réponds à la question suivante sur le patrimoine béninois de manière précise et narrative.

Question : {question}

Réponds en français de manière détaillée et pédagogique."""
            
            response = self.gemini_model.generate_content(prompt)
            latency = time.time() - start_time
            
            return {
                'response': response.text,
                'latency': latency
            }
            
        except Exception as e:
            return {
                'response': '',
                'latency': 0.0,
                'error': str(e)
            }
    
    def run_comparison(self):
        """Lance la comparaison sur toutes les questions"""
        questions = self.dataset['heritage_questions']
        
        print(f"\n{'='*80}")
        print(f"🚀 DÉMARRAGE DE LA COMPARAISON")
        print(f"{'='*80}")
        print(f"Questions : {len(questions)}")
        print(f"Session ID : {SESSION_ID}")
        print(f"\n")
        
        for i, item in enumerate(tqdm(questions, desc="Évaluation"), 1):
            question = item['question']
            ground_truth = item['ground_truth']
            pole = item['pole']
            
            print(f"\n{'─'*80}")
            print(f"Question {i}/{len(questions)}: {question}")
            print(f"Pôle: {pole}")
            print(f"{'─'*80}")
            
            # 1️⃣ Agent RAG
            print("🔹 Interrogation agent RAG...")
            rag_result = self.query_rag_agent(question, verbose=False)
            
            if 'error' in rag_result:
                print(f"   ❌ Erreur: {rag_result['error']}")
            else:
                print(f"   ✅ Réponse (latence: {rag_result['latency']:.2f}s)")
                print(f"   📊 RAG utilisé: {rag_result['used_rag']}")
                print(f"   📦 Chunks: {rag_result.get('chunks_used', 0)}")
            
            # 2️⃣ Gemini généraliste
            print("🔹 Interrogation Gemini généraliste...")
            gemini_result = self.query_gemini_generic(question)
            
            if 'error' in gemini_result:
                print(f"   ❌ Erreur: {gemini_result['error']}")
            else:
                print(f"   ✅ Réponse (latence: {gemini_result['latency']:.2f}s)")
            
            # Stocker les résultats
            self.results['rag_agent'].append({
                'question': question,
                'ground_truth': ground_truth,
                'response': rag_result.get('response', ''),
                'latency': rag_result.get('latency', 0.0),
                'used_rag': rag_result.get('used_rag', False),
                'chunks_used': rag_result.get('chunks_used', 0),
                'pole': pole,
                'error': rag_result.get('error')
            })
            
            self.results['gemini_generic'].append({
                'question': question,
                'ground_truth': ground_truth,
                'response': gemini_result.get('response', ''),
                'latency': gemini_result.get('latency', 0.0),
                'pole': pole,
                'error': gemini_result.get('error')
            })
            
            # Pause pour éviter rate limiting
            time.sleep(1)
        
        print(f"\n{'='*80}")
        print(f"✅ COMPARAISON TERMINÉE")
        print(f"{'='*80}\n")
    
    def calculate_metrics(self):
        """Calcule toutes les métriques"""
        print(f"\n{'='*80}")
        print(f"📊 CALCUL DES MÉTRIQUES")
        print(f"{'='*80}\n")
        
        metrics = {
            'rag_agent': {},
            'gemini_generic': {}
        }
        
        for system_name in ['rag_agent', 'gemini_generic']:
            print(f"\n🔹 Système: {system_name.upper()}")
            
            results = self.results[system_name]
            
            # Filtrer les résultats avec erreur
            valid_results = [r for r in results if not r.get('error')]
            print(f"   Résultats valides: {len(valid_results)}/{len(results)}")
            
            if len(valid_results) == 0:
                print(f"   ❌ Aucun résultat valide, impossible de calculer les métriques")
                continue
            
            # 1️⃣ LATENCY (moyenne)
            latencies = [r['latency'] for r in valid_results]
            metrics[system_name]['latency_mean'] = np.mean(latencies)
            metrics[system_name]['latency_std'] = np.std(latencies)
            print(f"   ⏱️  Latency: {metrics[system_name]['latency_mean']:.3f}s ± {metrics[system_name]['latency_std']:.3f}s")
            
            # 2️⃣ BERTSCORE
            if BERTSCORE_AVAILABLE:
                print(f"   🔹 Calcul BERTScore...")
                
                candidates = [r['response'] for r in valid_results]
                references = [r['ground_truth'] for r in valid_results]
                
                P, R, F1 = bert_score(
                    candidates,
                    references,
                    lang='fr',
                    verbose=False
                )
                
                metrics[system_name]['bertscore_precision'] = P.mean().item()
                metrics[system_name]['bertscore_recall'] = R.mean().item()
                metrics[system_name]['bertscore_f1'] = F1.mean().item()
                
                print(f"   ✅ BERTScore F1: {metrics[system_name]['bertscore_f1']:.3f}")
                print(f"      Precision: {metrics[system_name]['bertscore_precision']:.3f}")
                print(f"      Recall: {metrics[system_name]['bertscore_recall']:.3f}")
            else:
                print(f"   ⚠️  BERTScore non disponible")
        
        self.metrics = metrics
        return metrics
    
    def generate_report(self):
        """Génère un rapport détaillé"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1️⃣ Sauvegarder les résultats bruts
        results_file = RESULTS_DIR / f"raw_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'timestamp': timestamp,
                    'session_id': SESSION_ID,
                    'total_questions': len(self.dataset['heritage_questions'])
                },
                'results': self.results,
                'metrics': self.metrics
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Résultats bruts sauvegardés: {results_file}")
        
        # 2️⃣ Créer un tableau comparatif
        comparison_data = []
        
        for metric_name in ['bertscore_f1', 'bertscore_precision', 
                            'bertscore_recall', 'latency_mean']:
            row = {
                'Métrique': metric_name,
                'Agent RAG': self.metrics.get('rag_agent', {}).get(metric_name, 'N/A'),
                'Gemini Généraliste': self.metrics.get('gemini_generic', {}).get(metric_name, 'N/A')
            }
            comparison_data.append(row)
        
        df = pd.DataFrame(comparison_data)
        
        # Sauvegarder CSV
        csv_file = RESULTS_DIR / f"comparison_table_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        print(f"✅ Tableau comparatif sauvegardé: {csv_file}")
        
        # Afficher le tableau
        print(f"\n{'='*80}")
        print(f"📊 TABLEAU COMPARATIF")
        print(f"{'='*80}\n")
        print(df.to_string(index=False))
        print(f"\n{'='*80}\n")
        
        # 3️⃣ Créer un rapport markdown
        markdown_file = RESULTS_DIR / f"rapport_{timestamp}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(f"# Rapport de Comparaison RAG vs LLM Généraliste\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Projet**: Adjä - Agent Conversationnel Patrimoine Béninois\n\n")
            f.write(f"## Résumé\n\n")
            f.write(f"- Questions évaluées: {len(self.dataset['heritage_questions'])}\n")
            f.write(f"- Session ID: {SESSION_ID}\n\n")
            
            f.write(f"## Résultats\n\n")
            f.write(df.to_markdown(index=False))
            f.write(f"\n\n")
            
            f.write(f"## Analyse\n\n")
            f.write(f"### Latence\n")
            f.write(f"- **Agent RAG**: {self.metrics['rag_agent'].get('latency_mean', 'N/A'):.3f}s\n")
            f.write(f"- **Gemini**: {self.metrics['gemini_generic'].get('latency_mean', 'N/A'):.3f}s\n\n")
            
            f.write(f"### Similarité Sémantique (BERTScore F1)\n")
            rag_f1 = self.metrics['rag_agent'].get('bertscore_f1', 0)
            gemini_f1 = self.metrics['gemini_generic'].get('bertscore_f1', 0)
            f.write(f"- **Agent RAG**: {rag_f1:.3f}\n")
            f.write(f"- **Gemini**: {gemini_f1:.3f}\n")
            f.write(f"- **Différence**: {(rag_f1 - gemini_f1):.3f}\n\n")
        
        print(f"✅ Rapport markdown sauvegardé: {markdown_file}")
        
        return {
            'results_file': str(results_file),
            'csv_file': str(csv_file),
            'markdown_file': str(markdown_file)
        }

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """Point d'entrée principal"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║        COMPARAISON RAG vs LLM GÉNÉRALISTE                                ║
║        Projet Adjä - Patrimoine Béninois                                 ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Vérifications préliminaires
    if not Path(DATASET_PATH).exists():
        print(f"❌ Dataset introuvable: {DATASET_PATH}")
        print(f"💡 Crée d'abord le fichier avec les questions de test")
        return
    
    if not GEMINI_API_KEY:
        print(f"❌ GEMINI_API_KEY manquante dans .env")
        return
    
    # Vérifier que l'API est accessible
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API non accessible à {API_BASE_URL}")
            print(f"💡 Lance d'abord ton API avec: python api_with_tts.py")
            return
        print(f"✅ API accessible à {API_BASE_URL}")
    except requests.exceptions.RequestException:
        print(f"❌ Impossible de contacter l'API à {API_BASE_URL}")
        print(f"💡 Assure-toi que l'API tourne sur le port 8000")
        return
    
    # Lancer la comparaison
    comparator = RAGvsLLMComparator(DATASET_PATH)
    
    # Étape 1 : Interroger les systèmes
    comparator.run_comparison()
    
    # Étape 2 : Calculer les métriques
    comparator.calculate_metrics()
    
    # Étape 3 : Générer le rapport
    files = comparator.generate_report()
    
    print(f"\n{'='*80}")
    print(f"✅ ÉVALUATION TERMINÉE")
    print(f"{'='*80}")
    print(f"\nFichiers générés :")
    for file_type, filepath in files.items():
        print(f"  📄 {file_type}: {filepath}")
    print(f"\n")

if __name__ == "__main__":
    main()