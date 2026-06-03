"""
Training pipeline for pure second-order Markov models.

The project uses Markov Chain order=2 in two forms:
- logic-level Markov: predicts QUERY_TYPE:table
- signature Markov: predicts QUERY_TYPE:table|params for cache-aware pre-fetch
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from config.settings import LOGS_CSV, MODELS_DIR, TEST_SPLIT_RATIO
from src.ml.feature_extractor import extract_markov_sequences, extract_signature_sequences
from src.ml.markov_predictor import MarkovPredictor


def train_all(logs_path: str = LOGS_CSV):
    print(f"Loading logs from {logs_path}...")
    df = pd.read_csv(logs_path)
    print(f"  {len(df):,} rows loaded.")

    print("\n[1/2] Training Markov Chain order=2 (logic-level states)...")
    sequences = extract_markov_sequences(df)
    split = int(len(sequences) * (1 - TEST_SPLIT_RATIO))
    train_seqs, test_seqs = sequences[:split], sequences[split:]

    markov = MarkovPredictor(order=2)
    markov.train(train_seqs)
    markov_acc = markov.evaluate(test_seqs)
    print(f"  Markov accuracy: {markov_acc:.4f} ({markov_acc * 100:.1f}%)")

    markov_path = os.path.join(MODELS_DIR, "markov_model.pkl")
    markov.save(markov_path)
    print(f"  Saved -> {markov_path}")

    print("\n[2/2] Training Markov Chain order=2 (exact query signatures)...")
    signature_sequences = extract_signature_sequences(df)
    split = int(len(signature_sequences) * (1 - TEST_SPLIT_RATIO))
    sig_train, sig_test = signature_sequences[:split], signature_sequences[split:]

    signature_markov = MarkovPredictor(order=2)
    signature_markov.train(sig_train)
    signature_acc = signature_markov.evaluate(sig_test)
    print(f"  Signature Markov accuracy: {signature_acc:.4f} ({signature_acc * 100:.1f}%)")

    signature_path = os.path.join(MODELS_DIR, "markov_signature_model.pkl")
    signature_markov.save(signature_path)
    print(f"  Saved -> {signature_path}")

    print("\n=== Training complete ===")
    return {
        "markov": {"model": markov, "accuracy": markov_acc},
        "signature_markov": {"model": signature_markov, "accuracy": signature_acc},
    }


if __name__ == "__main__":
    results = train_all()
    print(f"\nMarkov accuracy           : {results['markov']['accuracy'] * 100:.1f}%")
    print(f"Signature Markov accuracy : {results['signature_markov']['accuracy'] * 100:.1f}%")
