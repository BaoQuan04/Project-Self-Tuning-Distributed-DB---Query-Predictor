"""
LSTM-based next-query predictor using PyTorch.
Input:  sequence of seq_len state indices
Output: probability distribution over VOCAB_SIZE states
"""
import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from src.ml.feature_extractor import VOCAB_SIZE, state_to_idx, idx_to_state


class _LSTMModel(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int, hidden_dim: int, num_layers: int):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, num_layers=num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(self, x):
        emb = self.embed(x)
        out, _ = self.lstm(emb)
        return self.fc(out[:, -1, :])


class LSTMPredictor:
    def __init__(self, embed_dim: int = 32, hidden_dim: int = 64, num_layers: int = 2):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = _LSTMModel(VOCAB_SIZE, embed_dim, hidden_dim, num_layers).to(self.device)
        self.trained = False
        self.seq_len = 5

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 30, batch_size: int = 512, lr: float = 1e-3):
        self.seq_len = X.shape[1]
        Xt = torch.tensor(X, dtype=torch.long)
        yt = torch.tensor(y, dtype=torch.long)
        dataset = TensorDataset(Xt, yt)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.CrossEntropyLoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

        self.model.train()
        for epoch in range(epochs):
            total_loss = 0.0
            for xb, yb in loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                optimizer.zero_grad()
                logits = self.model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            avg_loss = total_loss / len(loader)
            scheduler.step(avg_loss)
            if (epoch + 1) % 5 == 0:
                print(f"  Epoch {epoch+1}/{epochs}  loss={avg_loss:.4f}")

        self.trained = True

    def predict_top_k(self, recent_states: list, k: int = 3):
        if not self.trained:
            raise RuntimeError("Model not trained.")
        self.model.eval()
        idxs = [state_to_idx(s) for s in recent_states]
        # pad or truncate to seq_len
        if len(idxs) < self.seq_len:
            idxs = [0] * (self.seq_len - len(idxs)) + idxs
        else:
            idxs = idxs[-self.seq_len:]

        x = torch.tensor([idxs], dtype=torch.long).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        top_k = np.argsort(probs)[::-1][:k]
        return [(idx_to_state(int(i)), float(probs[i])) for i in top_k]

    def predict_next(self, recent_states: list):
        results = self.predict_top_k(recent_states, k=1)
        return results[0] if results else ("SELECT:products", 0.0)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> float:
        self.model.eval()
        Xt = torch.tensor(X, dtype=torch.long).to(self.device)
        with torch.no_grad():
            logits = self.model(Xt)
            preds = logits.argmax(dim=-1).cpu().numpy()
        return float((preds == y).mean())

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save({
            "model_state": self.model.state_dict(),
            "seq_len": self.seq_len,
            "trained": self.trained,
        }, path)

    @classmethod
    def load(cls, path: str) -> "LSTMPredictor":
        predictor = cls()
        checkpoint = torch.load(path, map_location=predictor.device)
        predictor.model.load_state_dict(checkpoint["model_state"])
        predictor.seq_len = checkpoint["seq_len"]
        predictor.trained = checkpoint["trained"]
        predictor.model.eval()
        return predictor
