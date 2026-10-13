
import joblib
from pathlib import Path
from typing import Any
from designkit.behavioral.typing import Assertion

from nexis.classifier import ActionClassifier
from nexis.errors import InvalidModelArtifactError, ModelArtifactNotFoundError
from nexis.forecaster import TimesFMForecaster
from nexis.config import MODEL_PATH, lru_cache


# ================================================== #
# FEATURES                                           #
# ================================================== #

@lru_cache()
def load_model(model_path: Path | None = None) -> ActionClassifier:
    Assertion(model_path).must_be(Path, None)

    artifact_path: Path = model_path or Path(MODEL_PATH)
    if not artifact_path.exists():
        raise ModelArtifactNotFoundError(artifact_path=artifact_path)
    
    model: Any = joblib.load(artifact_path)
    if not isinstance(model, ActionClassifier):
        raise InvalidModelArtifactError(artifact_path=artifact_path)
    
    return model


def load_forecaster() -> TimesFMForecaster:
    """
    Returns the shared TimesFM forecaster instance. Unlike `load_model`,
    this is not tied to a trained artifact: TimesFM is a pretrained
    foundation model used purely for zero-shot inference.
    """

    return TimesFMForecaster()
