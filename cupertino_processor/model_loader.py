"""
Model Loader - YOLO model loading and caching.

This module provides the ModelLoader class which handles loading YOLO models
from disk, caching them in memory, and providing access to the current model.

Supports complete model catalog:
- YOLO11 and YOLO12 versions
- All variants: n, s, m, l, x
- Both ONNX (320, 640) and PT (flexible) formats

Thread Safety:
- NOT thread-safe by design (single writer pattern)
- Only accessed from Control Plane thread for loading
- Only accessed from Inference Thread for reading (via lock in service)
"""

from pathlib import Path
from typing import Dict, Optional, Any
from ultralytics import YOLO
from cupertino_processor.config import ModelConfig


class ModelLoader:
    """
    YOLO model loader with in-memory caching.

    This class manages loading YOLO models and caching them in memory.
    Models are identified by (version, variant, input_size, format) tuples.

    Supports complete catalog:
    - YOLO11 / YOLO12
    - Variants: n, s, m, l, x
    - Formats: ONNX (fixed 320/640), PT (flexible)

    Thread Safety:
    - NOT inherently thread-safe (no internal locks)
    - Service layer must provide synchronization via _model_lock
    - Single writer pattern: Only Control Plane thread loads models

    Usage:
        loader = ModelLoader(models_dir=Path("./models"))

        # Load model using ModelConfig
        config = ModelConfig(model_version="12", model_variant="n", 
                           input_size=640, model_format="onnx")
        model = loader.load_model_from_config(config)

        # Or load directly
        model = loader.load_model(version="12", variant="n", 
                                 input_size=640, format="onnx")

        # Get current model
        current = loader.get_current_model()

        # List available models on disk
        available = loader.list_available_models()
    """

    def __init__(self, models_dir: Path):
        """
        Initialize model loader.

        Args:
            models_dir: Directory containing YOLO model files (.pt, .onnx)
        """
        self.models_dir = models_dir
        self._cache: Dict[tuple, YOLO] = {}
        self._current_model: Optional[YOLO] = None
        self._current_key: Optional[tuple] = None
        self._current_config: Optional[ModelConfig] = None

    def load_model_from_config(self, config: ModelConfig) -> YOLO:
        """
        Load YOLO model from ModelConfig.

        Args:
            config: ModelConfig with version, variant, size, format

        Returns:
            YOLO model instance

        Raises:
            FileNotFoundError: If model file does not exist
            ValueError: If configuration is invalid (validated by ModelConfig)
        """
        return self.load_model(
            version=config.model_version,
            variant=config.model_variant,
            input_size=config.input_size,
            model_format=config.model_format,
            confidence=config.confidence,
            iou_threshold=config.iou_threshold,
            config=config
        )

    def load_model(
        self,
        version: str = "12",
        variant: str = "n",
        input_size: int = 640,
        model_format: str = "onnx",
        confidence: float = 0.5,
        iou_threshold: float = 0.5,
        config: Optional[ModelConfig] = None
    ) -> YOLO:
        """
        Load YOLO model from disk or cache.

        Args:
            version: YOLO version ("11" or "12")
            variant: Model variant (n, s, m, l, x)
            input_size: Input image size (320, 640 for ONNX; flexible for PT)
            model_format: Model format ("onnx" or "pt")
            confidence: Detection confidence threshold
            iou_threshold: NMS IoU threshold
            config: Optional ModelConfig (for storing current config)

        Returns:
            YOLO model instance

        Raises:
            FileNotFoundError: If model file does not exist
            ValueError: If parameters are invalid

        Caching Strategy:
        - Cache key: (version, variant, input_size, format)
        - Cache hit: Return cached model (reconfigure thresholds)
        - Cache miss: Load from disk, cache, and return
        """
        # Build cache key
        cache_key = (version, variant, input_size, model_format)

        # Check cache
        if cache_key in self._cache:
            self._current_model = self._cache[cache_key]
            self._current_key = cache_key
            self._current_config = config
            
            # Update inference parameters (not cached)
            self._current_model.overrides["conf"] = confidence
            self._current_model.overrides["iou"] = iou_threshold
            
            return self._current_model

        # Determine model filename
        if model_format == "onnx":
            filename = f"yolo{version}{variant}-{input_size}.onnx"
        else:  # pt
            filename = f"yolo{version}{variant}.pt"

        model_path = self.models_dir / filename

        # Check if file exists
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Expected: {filename}\n"
                f"Available models:\n" + "\n".join(f"  - {m}" for m in self.list_available_models())
            )

        # Load model
        model = YOLO(str(model_path))

        # Configure model for inference
        model.overrides["verbose"] = False
        model.overrides["imgsz"] = input_size
        model.overrides["conf"] = confidence
        model.overrides["iou"] = iou_threshold

        # Cache and set as current
        self._cache[cache_key] = model
        self._current_model = model
        self._current_key = cache_key
        self._current_config = config

        return model

    def get_current_model(self) -> Optional[YOLO]:
        """
        Get the currently loaded model.

        Returns:
            Current YOLO model or None if no model loaded

        Thread Safety:
        - Safe to call from any thread if protected by external lock
        - Service layer must synchronize access via _model_lock
        """
        return self._current_model

    def get_current_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model info:
            - version: str
            - variant: str
            - input_size: int
            - format: str
            - model_path: str

            Returns None if no model is loaded.
        """
        if self._current_key is None:
            return None

        version, variant, input_size, model_format = self._current_key
        
        # Reconstruct filename
        if model_format == "onnx":
            filename = f"yolo{version}{variant}-{input_size}.onnx"
        else:
            filename = f"yolo{version}{variant}.pt"
        
        model_path = self.models_dir / filename

        return {
            "version": version,
            "variant": variant,
            "input_size": input_size,
            "format": model_format,
            "model_path": str(model_path),
        }
    
    def get_current_config(self) -> Optional[ModelConfig]:
        """
        Get the ModelConfig used to load the current model.

        Returns:
            ModelConfig or None if no model is loaded or config not available.
        """
        return self._current_config

    def list_available_models(self) -> list[str]:
        """
        List available YOLO models in models_dir.

        Returns:
            Sorted list of model filenames found in models_dir.

        Example:
            ["yolo11n-320.onnx", "yolo11n-640.onnx", "yolo11n.pt", ...]
        """
        if not self.models_dir.exists():
            return []

        models = []
        
        # Find all YOLO11/12 .pt files
        models.extend([
            f.name
            for f in self.models_dir.glob("yolo1[12]*.pt")
            if f.is_file()
        ])
        
        # Find all YOLO11/12 .onnx files
        models.extend([
            f.name
            for f in self.models_dir.glob("yolo1[12]*.onnx")
            if f.is_file()
        ])
        
        return sorted(models)

    def clear_cache(self) -> None:
        """
        Clear the model cache.

        WARNING: This will unload all models from memory.
        Current model reference will be set to None.

        Use with caution - only call when pipeline is stopped.
        """
        self._cache.clear()
        self._current_model = None
        self._current_key = None

    def cache_size(self) -> int:
        """
        Get the number of models in cache.

        Returns:
            Number of cached models.
        """
        return len(self._cache)
