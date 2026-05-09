"""
NNUE (Efficiently Updatable Neural Network) оценка.

Архитектура: 768 -> 256 (ReLU) -> 1
Две половины (для белых и чёрных) с общими весами, но зеркальными признаками.

Формат весов (.npz):
  - feature_weights: numpy array формы (256, 768)
  - feature_biases: numpy array формы (256,)
  - output_weights: numpy array формы (1, 512) - конкатенация белой и чёрной половин
  - output_bias: numpy array формы (1,)
"""

import chess
import numpy as np
from pathlib import Path
from .nnue_features import compute_features, NUM_FEATURES


class NNUE:
    """NNUE оценщик с инференсом на numpy."""
    
    def __init__(self, weights_path: str | Path | None = None):
        """
        Инициализация NNUE с весами из .npz файла.
        
        Если weights_path не указан, создаётся случайная сеть
        (для тестирования до обучения).
        """
        self.feature_weights = None
        self.feature_biases = None
        self.output_weights = None
        self.output_bias = None
        
        if weights_path is not None:
            self.load_weights(weights_path)
        else:
            self._init_random()
    
    def _init_random(self):
        """Инициализация случайными весами (для тестирования)."""
        rng = np.random.RandomState(42)
        self.feature_weights = rng.randn(256, NUM_FEATURES).astype(np.float32) * 0.1
        self.feature_biases = rng.randn(256).astype(np.float32) * 0.1
        self.output_weights = rng.randn(1, 512).astype(np.float32) * 0.1
        self.output_bias = rng.randn(1).astype(np.float32) * 0.1
    
    def load_weights(self, path: str | Path):
        """
        Загрузка весов из .npz файла.

        Ожидаемые ключи:
            - feature_weights: (hidden, 768)
            - feature_biases: (hidden,)
            - output_weights: (1, hidden*2)
            - output_bias: (1,)

        Размер hidden определяется автоматически из загруженных весов.
        """
        data = np.load(str(path))

        self.feature_weights = data['feature_weights'].astype(np.float32)
        self.feature_biases = data['feature_biases'].astype(np.float32)
        self.output_weights = data['output_weights'].astype(np.float32)
        self.output_bias = data['output_bias'].astype(np.float32)

        hidden = self.feature_weights.shape[0]

        assert self.feature_weights.shape == (hidden, NUM_FEATURES), \
            f"Expected feature_weights shape ({hidden}, {NUM_FEATURES}), got {self.feature_weights.shape}"
        assert self.feature_biases.shape == (hidden,), \
            f"Expected feature_biases shape ({hidden},), got {self.feature_biases.shape}"
        assert self.output_weights.shape == (1, hidden * 2), \
            f"Expected output_weights shape (1, {hidden * 2}), got {self.output_weights.shape}"
        assert self.output_bias.shape == (1,), \
            f"Expected output_bias shape (1,), got {self.output_bias.shape}"
    
    def save_weights(self, path: str | Path):
        """Сохранение весов в .npz файл."""
        np.savez(
            str(path),
            feature_weights=self.feature_weights,
            feature_biases=self.feature_biases,
            output_weights=self.output_weights,
            output_bias=self.output_bias,
        )
    
    def _forward_half(self, features: np.ndarray, is_white: bool) -> np.ndarray:
        """
        Прямой проход через одну половину сети.
        
        Args:
            features: вектор признаков (768,)
            is_white: True для белой половины, False для чёрной
        
        Returns:
            Активации скрытого слоя (256,)
        """
        if not is_white:
            features = features.copy()
            for sq in range(64):
                for i in range(6):
                    white_idx = i * 64 + sq
                    black_idx = (i + 6) * 64 + sq
                    features[white_idx], features[black_idx] = \
                        features[black_idx], features[white_idx]
        
        hidden = np.dot(self.feature_weights, features) + self.feature_biases
        hidden = np.maximum(0, hidden)  # ReLU
        return hidden
    
    def evaluate(self, board: chess.Board) -> int:
        """
        Оценка позиции с точки зрения белых.
        
        Returns:
            Оценка в сантипешках (целое число).
        """
        features = compute_features(board).astype(np.float32)
        
        hidden_white = self._forward_half(features, is_white=True)
        
        hidden_black = self._forward_half(features, is_white=False)
        
        hidden = np.concatenate([hidden_white, hidden_black])
        output = np.dot(self.output_weights, hidden) + self.output_bias
        
        score = int(round(output[0] * 400))
        
        return score
    
    def evaluate_batched(self, boards: list[chess.Board]) -> list[int]:
        """
        Пакетная оценка нескольких позиций.
        """
        features_batch = np.array([compute_features(b) for b in boards], dtype=np.float32)
        
        hidden_white = np.dot(features_batch, self.feature_weights.T) + self.feature_biases
        hidden_white = np.maximum(0, hidden_white)
        
        features_black = features_batch.copy()
        for sq in range(64):
            for i in range(6):
                white_idx = i * 64 + sq
                black_idx = (i + 6) * 64 + sq
                temp = features_black[:, white_idx].copy()
                features_black[:, white_idx] = features_black[:, black_idx]
                features_black[:, black_idx] = temp
        
        hidden_black = np.dot(features_black, self.feature_weights.T) + self.feature_biases
        hidden_black = np.maximum(0, hidden_black)
        
        hidden = np.concatenate([hidden_white, hidden_black], axis=1)
        output = np.dot(hidden, self.output_weights.T) + self.output_bias
        
        return [int(round(s[0] * 400)) for s in output]


_nnue_instance = None


def get_nnue(weights_path: str | Path | None = None) -> NNUE:
    """Получить или создать глобальный экземпляр NNUE."""
    global _nnue_instance
    if _nnue_instance is None:
        _nnue_instance = NNUE(weights_path)
    return _nnue_instance


def set_nnue(instance: NNUE):
    """Установить глобальный экземпляр NNUE."""
    global _nnue_instance
    _nnue_instance = instance