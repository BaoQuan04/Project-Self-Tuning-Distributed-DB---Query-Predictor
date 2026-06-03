"""
Markov Chain predictor (order 1 or 2).
State = "QUERY_TYPE:table_name"  (e.g. "SELECT:products")
"""
import pickle
import os
from collections import defaultdict
from typing import List, Tuple


def _new_counter():
    return defaultdict(int)


class MarkovPredictor:
    def __init__(self, order: int = 2):
        self.order = order
        self.transition: dict = defaultdict(_new_counter)
        self.trained = False

    def train(self, sequences: List[List[str]]):
        for seq in sequences:
            for i in range(len(seq) - self.order):
                context = tuple(seq[i: i + self.order])
                next_state = seq[i + self.order]
                self.transition[context][next_state] += 1
        self.trained = True

    def predict_top_k(self, context: List[str], k: int = 3) -> List[Tuple[str, float]]:
        if not self.trained:
            raise RuntimeError("Model not trained yet.")
        key = tuple(context[-self.order:]) if len(context) >= self.order else tuple(context)
        counts = self.transition.get(key, {})
        if not counts:
            # fallback: most common overall next state
            return [("SELECT:products", 1.0)]
        total = sum(counts.values())
        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:k]
        return [(state, cnt / total) for state, cnt in ranked]

    def predict_next(self, context: List[str]) -> Tuple[str, float]:
        predictions = self.predict_top_k(context, k=1)
        return predictions[0] if predictions else ("SELECT:products", 0.0)

    def evaluate(self, sequences: List[List[str]]) -> float:
        correct = 0
        total = 0
        for seq in sequences:
            for i in range(len(seq) - self.order):
                context = seq[i: i + self.order]
                actual = seq[i + self.order]
                predicted, _ = self.predict_next(context)
                if predicted == actual:
                    correct += 1
                total += 1
        return correct / total if total > 0 else 0.0

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        transition = {context: dict(counts) for context, counts in self.transition.items()}
        with open(path, "wb") as f:
            pickle.dump({"order": self.order, "transition": transition, "trained": self.trained}, f)

    @classmethod
    def load(cls, path: str) -> "MarkovPredictor":
        with open(path, "rb") as f:
            data = pickle.load(f)
        m = cls(order=data["order"])
        m.transition = defaultdict(_new_counter, {k: defaultdict(int, v) for k, v in data["transition"].items()})
        m.trained = data["trained"]
        return m
