"""
Script principal d'évaluation de l'agent conversationnel Adjä
VERSION CORRIGÉE - Protection complète contre agent_response = None
"""

import os
import json
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# RAGAS
try:
    from ragas import evaluate
    from ragas.metrics.collections import (
        context_precision,
        faithfulness,
        answer_relevancy
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    print("⚠️  RAGAS non installé. Seules les métriques custom seront calculées.")
    RAGAS_AVAILABLE = False

# Custom metrics
from metrics_calculator import CustomMetricsCalculator

# Importer l'agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()


class AdjaEvaluator:
    """
    Évaluateur complet pour l'agent Adjä
    VERSION CORRIGÉE avec gestion robuste des erreurs
    """
    
    def __init__(
        self,
        agent,
        test_dataset_path: str = "test_dataset.json",
        output_dir: str = "results"
    ):
        self.agent = agent
        self.test_dataset_path = test_dataset_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        with open(test_dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.test_cases = data["test_cases"]
            self.metadata = data.get("metadata", {})
        
        self.custom_calculator = CustomMetricsCalculator()
        self.detailed_results = []
        
        print(f"✅ Évaluateur initialisé")
        print(f"   Dataset: {len(self.test_cases)} questions")
        print(f"   Sortie: {self.output_dir}")
    
    def _create_error_response(self, query: str, error_msg: str, language: str = "fr") -> Dict[str, Any]:
        """
        Crée une réponse d'erreur standardisée
        
        Args:
            query: Question posée
            error_msg: Message d'erreur
            language: Langue
            
        Returns:
            Dictionnaire de réponse d'erreur
        """
        return {
            "success": False,
            "error": error_msg,
            "query": query,
            "intent": "error",
            "used_rag": False,
            "response": f"[ERREUR: {error_msg}]",
            "images": [],
            "sources": [],
            "language": language,
            "chunks_used": 0
        }
    
    def run_evaluation(
        self,
        verbose: bool = True,
        save_responses: bool = True
    ) -> Dict[str, Any]:
        """
        Lance l'évaluation complète avec gestion robuste des erreurs
        """
        
        print("\n" + "="*80)
        print("🚀 LANCEMENT DE L'ÉVALUATION COMPLÈTE D'ADJÄ")
        print("="*80)
        
        ragas_data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        total = len(self.test_cases)
        errors_count = 0
        
        for i, test_case in enumerate(self.test_cases, 1):
            query = test_case["query"]
            
            if verbose:
                print(f"\n{'─'*80}")
                print(f"[{i}/{total}] Test: {query}")
                print(f"{'─'*80}")
            
            # Générer réponse avec l'agent (PROTECTION COMPLÈTE)
            agent_response = None
            
            try:
                agent_response = self.agent.generate_response(
                    query=query,
                    language="fr",
                    verbose=False
                )
                
                # 🔧 PROTECTION 1: Agent renvoie None
                if agent_response is None:
                    errors_count += 1
                    print(f"⚠️  ERREUR: L'agent a renvoyé None pour: '{query}'")
                    agent_response = self._create_error_response(
                        query, 
                        "Agent returned None - Bug dans generate_response()",
                        "fr"
                    )
                
                # 🔧 PROTECTION 2: Agent renvoie autre chose qu'un dict
                elif not isinstance(agent_response, dict):
                    errors_count += 1
                    print(f"⚠️  ERREUR: L'agent a renvoyé type {type(agent_response)} au lieu de dict")
                    agent_response = self._create_error_response(
                        query,
                        f"Agent returned {type(agent_response)} instead of dict",
                        "fr"
                    )
                
                # ✅ Réponse valide
                else:
                    if verbose:
                        print(f"Intent détectée: {agent_response.get('intent', 'N/A')}")
                        print(f"RAG utilisé: {agent_response.get('used_rag', False)}")
                        if agent_response.get('used_rag'):
                            print(f"Chunks: {agent_response.get('chunks_used', 'N/A')}")
                
            except Exception as e:
                errors_count += 1
                print(f"❌ Exception lors de la génération: {type(e).__name__}: {str(e)}")
                agent_response = self._create_error_response(
                    query,
                    f"Exception: {type(e).__name__}: {str(e)}",
                    "fr"
                )
            
            # Enregistrer résultat
            detailed_result = {
                "test_id": test_case["id"],
                "query": query,
                "test_case": test_case,
                "agent_response": agent_response,
                "timestamp": datetime.now().isoformat(),
                "had_error": agent_response.get("intent") == "error"
            }
            self.detailed_results.append(detailed_result)
            
            # Ajouter au calculateur custom
            self.custom_calculator.add_result(test_case, agent_response)
            
            # Préparer pour RAGAS (seulement si succès + ground_truth)
            if (
                test_case["should_use_rag"] 
                and test_case.get("ground_truth")
                and agent_response.get("success", False)
                and agent_response.get("intent") != "error"
            ):
                ragas_data["question"].append(query)
                ragas_data["answer"].append(agent_response.get("response", ""))
                ragas_data["ground_truth"].append(test_case["ground_truth"])
                
                contexts = self._extract_contexts(agent_response)
                ragas_data["contexts"].append(contexts)
        
        print(f"\n✅ {total} tests exécutés")
        if errors_count > 0:
            print(f"⚠️  {errors_count} erreurs détectées (agent a renvoyé None ou exception)")
        
        # Métriques custom
        print("\n" + "="*80)
        print("📊 CALCUL DES MÉTRIQUES CUSTOM")
        print("="*80)
        
        custom_metrics = self.custom_calculator.generate_summary()
        self.custom_calculator.print_summary()
        
        # Métriques RAGAS
        ragas_metrics = {}
        
        if RAGAS_AVAILABLE and ragas_data["question"]:
            print("\n" + "="*80)
            print("📊 CALCUL DES MÉTRIQUES RAGAS")
            print("="*80)
            
            try:
                ragas_metrics = self._calculate_ragas_metrics(ragas_data, verbose)
            except Exception as e:
                print(f"❌ Erreur RAGAS: {e}")
                ragas_metrics = {"error": str(e)}
        else:
            if not RAGAS_AVAILABLE:
                print("\n⚠️  RAGAS non disponible")
            else:
                print(f"\n⚠️  Aucune question valide pour RAGAS ({len(ragas_data['question'])} questions)")
        
        # Résultats finaux
        final_results = {
            "metadata": {
                "evaluation_date": datetime.now().isoformat(),
                "dataset": self.metadata,
                "total_tests": total,
                "errors_count": errors_count,
                "ragas_tests": len(ragas_data["question"])
            },
            "custom_metrics": custom_metrics,
            "ragas_metrics": ragas_metrics,
            "detailed_results": self.detailed_results if save_responses else []
        }
        
        self._save_results(final_results)
        self._print_final_summary(final_results)
        
        return final_results
    
    def _extract_contexts(self, agent_response: Dict[str, Any]) -> List[str]:
        """Extrait les contextes RAG"""
        
        contexts = []
        
        if "retrieved_chunks" in agent_response:
            contexts = [chunk["text"] for chunk in agent_response["retrieved_chunks"]]
        elif agent_response.get("used_rag"):
            try:
                query = agent_response.get("query", "")
                llm_context = self.agent.retrieve_context(query, verbose=False)
                
                if llm_context:
                    contexts = [llm_context["context"]]
            except Exception as e:
                print(f"⚠️  Impossible de récupérer contexte: {e}")
                contexts = [""]
        
        if not contexts:
            contexts = [""]
        
        return contexts
    
    def _calculate_ragas_metrics(
        self,
        ragas_data: Dict[str, List],
        verbose: bool = True
    ) -> Dict[str, float]:
        """Calcule les métriques RAGAS"""
        
        if verbose:
            print(f"Questions à évaluer: {len(ragas_data['question'])}")
        
        dataset = Dataset.from_dict(ragas_data)
        
        if verbose:
            print("Calcul des métriques RAGAS en cours...")
            print("(Cela peut prendre quelques minutes)")
        
        results = evaluate(
            dataset,
            metrics=[
                context_precision,
                faithfulness,
                answer_relevancy
            ]
        )
        
        metrics = {
            "context_precision": float(results.get("context_precision", 0)),
            "faithfulness": float(results.get("faithfulness", 0)),
            "answer_relevancy": float(results.get("answer_relevancy", 0))
        }
        
        if verbose:
            print("\n✅ Métriques RAGAS calculées:")
            print(f"   Context Precision: {metrics['context_precision']:.4f}")
            print(f"   Faithfulness:      {metrics['faithfulness']:.4f}")
            print(f"   Answer Relevancy:  {metrics['answer_relevancy']:.4f}")
        
        return metrics
    
    def _save_results(self, results: Dict[str, Any]):
        """Sauvegarde les résultats"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        full_path = self.output_dir / f"evaluation_results_{timestamp}.json"
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés: {full_path}")
        
        summary = {
            "date": results["metadata"]["evaluation_date"],
            "total_tests": results["metadata"]["total_tests"],
            "errors_count": results["metadata"]["errors_count"],
            "custom_metrics": {
                "intent_accuracy": results["custom_metrics"]["intent_detection"]["overall"],
                "rag_accuracy": results["custom_metrics"]["rag_activation"]["accuracy"],
                "rag_precision": results["custom_metrics"]["rag_activation"]["precision"],
                "rag_recall": results["custom_metrics"]["rag_activation"]["recall"]
            },
            "ragas_metrics": results["ragas_metrics"]
        }
        
        summary_path = self.output_dir / f"summary_{timestamp}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résumé sauvegardé: {summary_path}")
    
    def _print_final_summary(self, results: Dict[str, Any]):
        """Affiche le résumé final"""
        
        print("\n" + "="*80)
        print("🎯 RÉSUMÉ FINAL DE L'ÉVALUATION")
        print("="*80)
        
        custom = results["custom_metrics"]
        print(f"\n📊 MÉTRIQUES CUSTOM:")
        print(f"   Intent Detection Accuracy: {custom['intent_detection']['overall']:.2%}")
        print(f"   RAG Activation Accuracy:   {custom['rag_activation']['accuracy']:.2%}")
        print(f"   RAG Precision:             {custom['rag_activation']['precision']:.2%}")
        print(f"   RAG Recall:                {custom['rag_activation']['recall']:.2%}")
        print(f"   RAG F1 Score:              {custom['rag_activation']['f1_score']:.2%}")
        
        if results["ragas_metrics"] and "error" not in results["ragas_metrics"]:
            ragas = results["ragas_metrics"]
            print(f"\n📊 MÉTRIQUES RAGAS:")
            print(f"   Context Precision: {ragas['context_precision']:.4f}")
            print(f"   Faithfulness:      {ragas['faithfulness']:.4f}")
            print(f"   Answer Relevancy:  {ragas['answer_relevancy']:.4f}")
        
        errors = custom["error_analysis"]
        print(f"\n❌ ERREURS:")
        print(f"   Erreurs d'intention:  {len(errors['intent_errors'])}")
        print(f"   Erreurs décision RAG: {len(errors['rag_activation_errors'])}")
        
        if results["metadata"]["errors_count"] > 0:
            print(f"\n⚠️  BUGS AGENT:")
            print(f"   {results['metadata']['errors_count']} questions ont causé un crash (None ou exception)")
        
        print("\n" + "="*80)
        print("✅ ÉVALUATION TERMINÉE")
        print("="*80 + "\n")


def main():
    """Point d'entrée principal"""
    
    print("🔧 Configuration de l'évaluation...")
    
    if not os.getenv("PINECONE_API_KEY"):
        print("❌ PINECONE_API_KEY manquante dans .env")
        return
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY manquante dans .env")
        return
    
    # Importer l'agent
    from rag_conversational_agent_correction import BeninHeritageConversationalAgent

    agent = BeninHeritageConversationalAgent(
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        index_name=os.getenv("INDEX_NAME", "benin-heritage")
    )
    
    evaluator = AdjaEvaluator(
        agent=agent,
        test_dataset_path="test_dataset.json",
        output_dir="results"
    )
    
    evaluator.run_evaluation(
        verbose=True,
        save_responses=True
    )
    
    print("\n✅ Évaluation terminée avec succès!")
    print(f"Consulte les résultats dans: {evaluator.output_dir}")


if __name__ == "__main__":
    main()