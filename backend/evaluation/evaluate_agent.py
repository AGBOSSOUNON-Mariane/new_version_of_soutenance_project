"""
Script principal d'évaluation de l'agent conversationnel Adjä
VERSION COMPATIBLE RAGAS 0.4.3 avec Gemini (LLM + Embeddings)
"""

import os
import json
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# RAGAS 0.4.3 avec Gemini
try:
    from ragas import evaluate
    from ragas.metrics import (
        context_precision,
        faithfulness,
        answer_relevancy
    )
    from datasets import Dataset
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    RAGAS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  RAGAS non installé complètement: {e}")
    print("   Installez: pip install ragas langchain-google-genai")
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
    VERSION COMPATIBLE RAGAS 0.4.3
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
        
        # 🔧 Configuration de Gemini pour RAGAS 0.4.3 (LLM + Embeddings)
        self.ragas_llm = None
        self.ragas_embeddings = None
        
        if RAGAS_AVAILABLE:
            try:
                print("🤖 Configuration de Gemini pour RAGAS 0.4.3...")
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                
                if not gemini_api_key:
                    print("❌ GEMINI_API_KEY manquante dans .env")
                else:
                    # LLM pour les évaluations
                    self.ragas_llm = ChatGoogleGenerativeAI(
                        model="gemini-2.0-flash-exp",
                        google_api_key=gemini_api_key,
                        temperature=0
                    )
                    
                    # 🔧 Embeddings Gemini (pour remplacer OpenAI)
                    self.ragas_embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/embedding-001",
                        google_api_key=gemini_api_key
                    )
                    
                    print("✅ RAGAS configuré avec Gemini (LLM + Embeddings)")
            except Exception as e:
                print(f"⚠️  Impossible de configurer RAGAS avec Gemini: {e}")
                self.ragas_llm = None
                self.ragas_embeddings = None
        
        print(f"✅ Évaluateur initialisé")
        print(f"   Dataset: {len(self.test_cases)} questions")
        print(f"   Sortie: {self.output_dir}")
    
    def _create_error_response(self, query: str, error_msg: str, language: str = "fr") -> Dict[str, Any]:
        """
        Crée une réponse d'erreur standardisée
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
        Lance l'évaluation complète avec Gemini pour RAGAS
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
            
            # Générer réponse avec l'agent
            agent_response = None
            
            try:
                agent_response = self.agent.generate_response(
                    query=query,
                    language="fr",
                    verbose=False
                )
                
                # Protection contre None
                if agent_response is None:
                    errors_count += 1
                    print(f"⚠️  ERREUR: L'agent a renvoyé None pour: '{query}'")
                    agent_response = self._create_error_response(
                        query, 
                        "Agent returned None",
                        "fr"
                    )
                
                # Protection contre type incorrect
                elif not isinstance(agent_response, dict):
                    errors_count += 1
                    print(f"⚠️  ERREUR: Type {type(agent_response)} au lieu de dict")
                    agent_response = self._create_error_response(
                        query,
                        f"Agent returned {type(agent_response)}",
                        "fr"
                    )
                
                # Réponse valide
                else:
                    if verbose:
                        print(f"Intent détectée: {agent_response.get('intent', 'N/A')}")
                        print(f"RAG utilisé: {agent_response.get('used_rag', False)}")
                        if agent_response.get('used_rag'):
                            print(f"Chunks: {agent_response.get('chunks_used', 'N/A')}")
                
            except Exception as e:
                errors_count += 1
                print(f"❌ Exception: {type(e).__name__}: {str(e)}")
                agent_response = self._create_error_response(
                    query,
                    f"Exception: {type(e).__name__}",
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
            
            # Préparer pour RAGAS
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
            print(f"⚠️  {errors_count} erreurs détectées")
        
        # Métriques custom
        print("\n" + "="*80)
        print("📊 CALCUL DES MÉTRIQUES CUSTOM")
        print("="*80)
        
        custom_metrics = self.custom_calculator.generate_summary()
        self.custom_calculator.print_summary()
        
        # Métriques RAGAS avec Gemini
        ragas_metrics = {}
        
        if RAGAS_AVAILABLE and self.ragas_llm and self.ragas_embeddings and ragas_data["question"]:
            print("\n" + "="*80)
            print("📊 CALCUL DES MÉTRIQUES RAGAS (avec Gemini)")
            print("="*80)
            
            try:
                ragas_metrics = self._calculate_ragas_metrics(ragas_data, verbose)
            except Exception as e:
                print(f"❌ Erreur RAGAS: {e}")
                import traceback
                traceback.print_exc()
                ragas_metrics = {"error": str(e)}
        else:
            if not RAGAS_AVAILABLE:
                print("\n⚠️  RAGAS non disponible")
            elif not self.ragas_llm or not self.ragas_embeddings:
                print("\n⚠️  Gemini non configuré complètement pour RAGAS")
            else:
                print(f"\n⚠️  Aucune question valide pour RAGAS ({len(ragas_data['question'])} questions)")
        
        # Résultats finaux
        final_results = {
            "metadata": {
                "evaluation_date": datetime.now().isoformat(),
                "dataset": self.metadata,
                "total_tests": total,
                "errors_count": errors_count,
                "ragas_tests": len(ragas_data["question"]),
                "ragas_llm": "gemini-2.0-flash-exp" if self.ragas_llm else None,
                "ragas_embeddings": "models/embedding-001" if self.ragas_embeddings else None,
                "ragas_version": "0.4.3"
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
            contexts = ["No context retrieved"]
        
        return contexts
    
    def _calculate_ragas_metrics(self, ragas_data, verbose=True):
        """Version simplifiée qui extrait correctement les scores"""
        
        dataset = Dataset.from_dict(ragas_data)
        
        try:
            results = evaluate(
                dataset,
                metrics=[context_precision, faithfulness, answer_relevancy],
                llm=self.ragas_llm,
                embeddings=self.ragas_embeddings
            )
        except Exception as e:
            return {"error": str(e)}
        
        # D'après votre debug, les scores sont dans _repr_dict
        scores = {}
        
        if hasattr(results, '_repr_dict'):
            scores = results._repr_dict.copy()
            print(f"✅ Scores extraits de _repr_dict: {scores}")
        
        elif hasattr(results, 'scores'):
            # Alternative: calculer depuis results.scores
            if isinstance(results.scores, list) and len(results.scores) > 0:
                for metric_name in ["context_precision", "faithfulness", "answer_relevancy"]:
                    values = []
                    for row in results.scores:
                        if metric_name in row:
                            try:
                                values.append(float(row[metric_name]))
                            except:
                                pass
                    
                    if values:
                        scores[metric_name] = sum(values) / len(values)
        
        return scores

    
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
            "ragas_llm": results["metadata"]["ragas_llm"],
            "ragas_embeddings": results["metadata"]["ragas_embeddings"],
            "ragas_version": results["metadata"]["ragas_version"],
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
            print(f"\n📊 MÉTRIQUES RAGAS (Gemini - v0.4.3):")
            print(f"   Context Precision: {ragas['context_precision']:.4f}")
            print(f"   Faithfulness:      {ragas['faithfulness']:.4f}")
            print(f"   Answer Relevancy:  {ragas['answer_relevancy']:.4f}")
        elif results["ragas_metrics"] and "error" in results["ragas_metrics"]:
            print(f"\n⚠️  RAGAS: {results['ragas_metrics']['error']}")
        
        errors = custom["error_analysis"]
        print(f"\n❌ ERREURS:")
        print(f"   Erreurs d'intention:  {len(errors['intent_errors'])}")
        print(f"   Erreurs décision RAG: {len(errors['rag_activation_errors'])}")
        
        if results["metadata"]["errors_count"] > 0:
            print(f"\n⚠️  BUGS AGENT:")
            print(f"   {results['metadata']['errors_count']} questions ont causé un crash")
        
        print("\n" + "="*80)
        print("✅ ÉVALUATION TERMINÉE")
        print("="*80 + "\n")


def main():
    """Point d'entrée principal"""
    
    print("🔧 Configuration de l'évaluation...")
    print("📌 RAGAS version: 0.4.3")
    
    # Vérifier les clés API
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

