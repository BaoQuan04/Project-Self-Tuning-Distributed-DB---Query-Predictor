"""
Feature extractor — converts raw query log rows into ML-ready features.
"""
import pandas as pd
import numpy as np
import json
from src.ml.query_signature import make_query_signature

TABLES = ["customers", "orders", "products", "inventory"]
QUERY_TYPES = ["SELECT", "INSERT", "UPDATE", "DELETE"]
STATES = [f"{qt}:{t}" for qt in QUERY_TYPES for t in TABLES]
STATE2IDX = {s: i for i, s in enumerate(STATES)}
IDX2STATE = {i: s for s, i in STATE2IDX.items()}
VOCAB_SIZE = len(STATES)


def state_to_idx(state: str) -> int:
    return STATE2IDX.get(state, 0)


def idx_to_state(idx: int) -> str:
    return IDX2STATE.get(idx, STATES[0])


def extract_sequences(df: pd.DataFrame, seq_len: int = 5) -> tuple:
    """
    Group by session_id, build sequences of state indices.
    Returns (X, y) where X.shape = (N, seq_len) and y.shape = (N,).
    """
    df = df.copy()
    df["state"] = df["query_type"] + ":" + df["table_name"]
    df["state_idx"] = df["state"].map(STATE2IDX).fillna(0).astype(int)
    df = df.sort_values(["session_id", "timestamp"])

    X, y = [], []
    for _, grp in df.groupby("session_id", sort=False):
        idxs = grp["state_idx"].tolist()
        for i in range(len(idxs) - seq_len):
            X.append(idxs[i: i + seq_len])
            y.append(idxs[i + seq_len])

    return np.array(X, dtype=np.int64), np.array(y, dtype=np.int64)


def extract_markov_sequences(df: pd.DataFrame) -> list:
    """Return flat list of state strings per session (for Markov training)."""
    df = df.copy()
    df["state"] = df["query_type"] + ":" + df["table_name"]
    df = df.sort_values(["session_id", "timestamp"])
    sequences = []
    for _, grp in df.groupby("session_id", sort=False):
        sequences.append(grp["state"].tolist())
    return sequences


def extract_signature_sequences(df: pd.DataFrame) -> list:
    """Return exact query signatures per session for cache-key prediction."""
    df = df.copy()

    def _signature(row):
        try:
            params = json.loads(row["query_params"])
        except Exception:
            params = {}
        return make_query_signature(row["query_type"], row["table_name"], params)

    df["signature"] = df.apply(_signature, axis=1)
    df = df.sort_values(["session_id", "timestamp"])
    sequences = []
    for _, grp in df.groupby("session_id", sort=False):
        sequences.append(grp["signature"].tolist())
    return sequences
