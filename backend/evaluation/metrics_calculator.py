"""
Calcul des métriques custom pour l'évaluation d'Adjä
Métriques non couvertes par RAGAS
"""

from typing import List, Dict, Any
from collections import defaultdict


class CustomMetricsCalculator:
    """
    Calculateur de métriques spécifiques à l'agent Adjä
    """
    
    def __init__(self):
        self.results = []
        self.confusion_matrix = {
            "intent": defaultdict(lambda: defaultdict(int)),
            "rag_activation": {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        }
    
    def add_result(
        self,
        test_case: Dict[str, Any],
        agent_response: Dict[str, Any]
    ):
        """
        Ajoute un résultat de test
        
        Args:
            test_case: Cas de test du dataset
            agent_response: Réponse de l'agent (peut être None en cas d'erreur)
        """
        
        # 🔧 CORRECTION: Gérer le cas où agent_response est None
        if agent_response is None:
            agent_response = {
                "intent": "error",
                "used_rag": False,
                "response": "[Erreur: Aucune réponse générée]"
            }
        
        result = {
            "test_id": test_case["id"],
            "query": test_case["query"],
            
            # Intent Detection
            "expected_intent": test_case["expected_intent"],
            "detected_intent": agent_response.get("intent", "unknown"),
            "intent_correct": test_case["expected_intent"] == agent_response.get("intent"),
            
            # RAG Activation
            "should_use_rag": test_case["should_use_rag"],
            "used_rag": agent_response.get("used_rag", False),
            "rag_decision_correct": test_case["should_use_rag"] == agent_response.get("used_rag", False),
            
            # Autres infos
            "pole": test_case.get("pole"),
            "response_preview": agent_response.get("response", "")[:100]
        }
        
        self.results.append(result)
        
        # Mise à jour matrice de confusion
        self._update_confusion_matrices(result)
    
    def _update_confusion_matrices(self, result: Dict[str, Any]):
        """Met à jour les matrices de confusion"""
        
        # Matrice Intent Detection
        expected = result["expected_intent"]
        detected = result["detected_intent"]
        self.confusion_matrix["intent"][expected][detected] += 1
        
        # Matrice RAG Activation (binaire)
        should_rag = result["should_use_rag"]
        used_rag = result["used_rag"]
        
        if should_rag and used_rag:
            self.confusion_matrix["rag_activation"]["tp"] += 1  # True Positive
        elif should_rag and not used_rag:
            self.confusion_matrix["rag_activation"]["fn"] += 1  # False Negative
        elif not should_rag and used_rag:
            self.confusion_matrix["rag_activation"]["fp"] += 1  # False Positive
        elif not should_rag and not used_rag:
            self.confusion_matrix["rag_activation"]["tn"] += 1  # True Negative
    
    def calculate_intent_detection_accuracy(self) -> Dict[str, float]:
        """
        Calcule l'accuracy de la détection d'intention
        
        Returns:
            Dict avec overall accuracy et accuracy par intention
        """
        
        if not self.results:
            return {"overall": 0.0}
        
        # Overall accuracy
        correct = sum(1 for r in self.results if r["intent_correct"])
        overall = correct / len(self.results)
        
        # Accuracy par intention
        intent_stats = defaultdict(lambda: {"correct": 0, "total": 0})
        
        for result in self.results:
            intent = result["expected_intent"]
            intent_stats[intent]["total"] += 1
            if result["intent_correct"]:
                intent_stats[intent]["correct"] += 1
        
        by_intent = {}
        for intent, stats in intent_stats.items():
            by_intent[intent] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
        
        return {
            "overall": round(overall, 4),
            "by_intent": {k: round(v, 4) for k, v in by_intent.items()},
            "confusion_matrix": dict(self.confusion_matrix["intent"])
        }
    
    def calculate_rag_activation_accuracy(self) -> Dict[str, float]:
        """
        Calcule les métriques de décision RAG
        
        Returns:
            Dict avec accuracy, precision, recall, F1
        """
        
        if not self.results:
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0
            }
        
        cm = self.confusion_matrix["rag_activation"]
        
        # Accuracy
        total = cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"]
        accuracy = (cm["tp"] + cm["tn"]) / total if total > 0 else 0.0
        
        # Precision: Parmi les fois où RAG a été activé, combien était correct ?
        precision = cm["tp"] / (cm["tp"] + cm["fp"]) if (cm["tp"] + cm["fp"]) > 0 else 0.0
        
        # Recall: Parmi les fois où RAG devait être activé, combien de fois l'a-t-il été ?
        recall = cm["tp"] / (cm["tp"] + cm["fn"]) if (cm["tp"] + cm["fn"]) > 0 else 0.0
        
        # F1 Score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": cm
        }
    
    def get_error_analysis(self) -> Dict[str, List[Dict]]:
        """
        Analyse détaillée des erreurs
        
        Returns:
            Dict avec listes d'erreurs par type
        """
        
        errors = {
            "intent_errors": [],
            "rag_activation_errors": [],
            "combined_errors": []
        }
        
        for result in self.results:
            # Erreurs d'intention
            if not result["intent_correct"]:
                errors["intent_errors"].append({
                    "test_id": result["test_id"],
                    "query": result["query"],
                    "expected": result["expected_intent"],
                    "detected": result["detected_intent"],
                    "response_preview": result["response_preview"]
                })
            
            # Erreurs de décision RAG
            if not result["rag_decision_correct"]:
                errors["rag_activation_errors"].append({
                    "test_id": result["test_id"],
                    "query": result["query"],
                    "should_use_rag": result["should_use_rag"],
                    "used_rag": result["used_rag"],
                    "intent": result["detected_intent"]
                })
            
            # Erreurs combinées (les deux à la fois)
            if not result["intent_correct"] and not result["rag_decision_correct"]:
                errors["combined_errors"].append({
                    "test_id": result["test_id"],
                    "query": result["query"],
                    "expected_intent": result["expected_intent"],
                    "detected_intent": result["detected_intent"],
                    "should_use_rag": result["should_use_rag"],
                    "used_rag": result["used_rag"]
                })
        
        return errors
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        Génère un résumé complet des métriques custom
        
        Returns:
            Dict avec toutes les métriques calculées
        """
        
        return {
            "total_tests": len(self.results),
            "intent_detection": self.calculate_intent_detection_accuracy(),
            "rag_activation": self.calculate_rag_activation_accuracy(),
            "error_analysis": self.get_error_analysis()
        }
    
    def print_summary(self):
        """Affiche un résumé formaté dans la console"""
        
        summary = self.generate_summary()
        
        print("\n" + "="*80)
        print("📊 MÉTRIQUES CUSTOM - RÉSUMÉ")
        print("="*80)
        
        print(f"\n📝 Total de tests: {summary['total_tests']}")
        
        # Intent Detection
        print("\n" + "─"*80)
        print("🎯 INTENT DETECTION ACCURACY")
        print("─"*80)
        intent = summary["intent_detection"]
        print(f"Overall Accuracy: {intent['overall']:.2%}")
        
        print("\nAccuracy par intention:")
        for intent_type, acc in intent["by_intent"].items():
            print(f"  • {intent_type:20s}: {acc:.2%}")
        
        # RAG Activation
        print("\n" + "─"*80)
        print("🔍 RAG ACTIVATION ACCURACY")
        print("─"*80)
        rag = summary["rag_activation"]
        print(f"Accuracy:  {rag['accuracy']:.2%}")
        print(f"Precision: {rag['precision']:.2%}  (Quand RAG activé, était-ce correct ?)")
        print(f"Recall:    {rag['recall']:.2%}  (Quand RAG nécessaire, a-t-il été activé ?)")
        print(f"F1 Score:  {rag['f1_score']:.2%}")
        
        cm = rag["confusion_matrix"]
        print(f"\nConfusion Matrix:")
        print(f"  TP (RAG correct activé):     {cm['tp']}")
        print(f"  TN (RAG correct non activé): {cm['tn']}")
        print(f"  FP (RAG activé à tort):      {cm['fp']}")
        print(f"  FN (RAG manqué):             {cm['fn']}")
        
        # Erreurs
        errors = summary["error_analysis"]
        print("\n" + "─"*80)
        print("❌ ANALYSE DES ERREURS")
        print("─"*80)
        print(f"Erreurs d'intention:      {len(errors['intent_errors'])}")
        print(f"Erreurs décision RAG:     {len(errors['rag_activation_errors'])}")
        print(f"Erreurs combinées:        {len(errors['combined_errors'])}")
        
        # Afficher quelques exemples d'erreurs
        if errors["intent_errors"]:
            print("\n🔴 Exemples d'erreurs d'intention:")
            for err in errors["intent_errors"][:3]:
                print(f"  • Query: '{err['query']}'")
                print(f"    Expected: {err['expected']}, Got: {err['detected']}")
        
        if errors["rag_activation_errors"]:
            print("\n🔴 Exemples d'erreurs de décision RAG:")
            for err in errors["rag_activation_errors"][:3]:
                print(f"  • Query: '{err['query']}'")
                print(f"    Should use RAG: {err['should_use_rag']}, Used: {err['used_rag']}")
        
        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # Test du calculateur
    calculator = CustomMetricsCalculator()
    
    # Simuler quelques résultats
    test_cases = [
        {
            "id": 1,
            "query": "Bonjour",
            "expected_intent": "greeting",
            "should_use_rag": False
        },
        {
            "id": 2,
            "query": "Qui est Ghézo ?",
            "expected_intent": "heritage_question",
            "should_use_rag": True
        }
    ]
    
    agent_responses = [
        {
            "intent": "greeting",
            "used_rag": False,
            "response": "Bonjour ! Je suis Adjä..."
        },
        {
            "intent": "heritage_question",
            "used_rag": True,
            "response": "Ghézo fut un grand roi..."
        }
    ]
    
    for test, response in zip(test_cases, agent_responses):
        calculator.add_result(test, response)
    
    calculator.print_summary()