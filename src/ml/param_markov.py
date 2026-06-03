"""
ParamMarkov — per-table Markov chain predicting query params.
Step 2 in the 2-step pipeline: LSTM predicts table, ParamMarkov predicts params.
"""
import json
import pickle
import os
from collections import defaultdict

from src.ml.markov_predictor import MarkovPredictor
from src.ml.query_signature import canonical_params


class ParamMarkov:
    def __init__(self, order: int = 2):
        self.order = order
        self._chains: dict = {}  # table → MarkovPredictor

    def train(self, df):
        df = df.copy()
        df = df.sort_values(["session_id", "timestamp"])

        table_sequences = defaultdict(list)  # table → list of param sequences

        for (session_id, table), group in df.groupby(["session_id", "table_name"], sort=False):
            seq = []
            for _, row in group.iterrows():
                try:
                    params = json.loads(row["query_params"])
                except Exception:
                    params = {}
                seq.append(canonical_params(params))

            if len(seq) > self.order:
                table_sequences[table].append(seq)

        for table, sequences in table_sequences.items():
            chain = MarkovPredictor(order=self.order)
            chain.train(sequences)
            self._chains[table] = chain
            total_states = sum(len(s) for s in sequences)
            print(f"    '{table}': {len(sequences):,} sessions, {total_states:,} param states")

    def predict_params(self, table: str, recent_param_strings: list):
        """
        Predict next params for a table given recent canonical param strings.
        Returns (params_dict, confidence).
        """
        chain = self._chains.get(table)
        if not chain or not recent_param_strings:
            return {"limit": 20}, 0.0

        predicted_sig, confidence = chain.predict_next(recent_param_strings)
        try:
            params = json.loads(predicted_sig)
        except Exception:
            params = {"limit": 20}
        return params, confidence

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"order": self.order, "chains": self._chains}, f)

    @classmethod
    def load(cls, path: str) -> "ParamMarkov":
        with open(path, "rb") as f:
            data = pickle.load(f)
        obj = cls(order=data["order"])
        obj._chains = data["chains"]
        return obj
