# YOLO Model Catalog

This directory contains pre-trained YOLO models in both ONNX and PyTorch formats.

## Available Models

### YOLO11 Models

| Variant | Input Size | Format | Filename | Size |
|---------|-----------|--------|----------|------|
| n (nano) | 320 | ONNX | yolo11n-320.onnx | ~10 MB |
| n (nano) | 640 | ONNX | yolo11n-640.onnx | ~10 MB |
| n (nano) | flexible | PT | yolo11n.pt | ~5.4 MB |
| s (small) | 320 | ONNX | yolo11s-320.onnx | ~36 MB |
| s (small) | 640 | ONNX | yolo11s-640.onnx | ~36 MB |
| s (small) | flexible | PT | yolo11s.pt | ~18 MB |
| m (medium) | 320 | ONNX | yolo11m-320.onnx | ~77 MB |
| m (medium) | 640 | ONNX | yolo11m-640.onnx | ~77 MB |
| m (medium) | flexible | PT | yolo11m.pt | ~39 MB |
| l (large) | 320 | ONNX | yolo11l-320.onnx | ~97 MB |
| l (large) | 640 | ONNX | yolo11l-640.onnx | ~97 MB |
| l (large) | flexible | PT | yolo11l.pt | ~49 MB |
| x (xlarge) | 320 | ONNX | yolo11x-320.onnx | ~217 MB |
| x (xlarge) | 640 | ONNX | yolo11x-640.onnx | ~217 MB |
| x (xlarge) | flexible | PT | yolo11x.pt | ~109 MB |

### YOLO12 Models

| Variant | Input Size | Format | Filename | Size |
|---------|-----------|--------|----------|------|
| n (nano) | 320 | ONNX | yolo12n-320.onnx | ~10 MB |
| n (nano) | 640 | ONNX | yolo12n-640.onnx | ~10 MB |
| n (nano) | flexible | PT | yolo12n.pt | ~5.3 MB |
| s (small) | 320 | ONNX | yolo12s-320.onnx | ~36 MB |
| s (small) | 640 | ONNX | yolo12s-640.onnx | ~36 MB |
| s (small) | flexible | PT | yolo12s.pt | ~18 MB |
| m (medium) | 320 | ONNX | yolo12m-320.onnx | ~77 MB |
| m (medium) | 640 | ONNX | yolo12m-640.onnx | ~77 MB |
| m (medium) | flexible | PT | yolo12m.pt | ~39 MB |
| l (large) | 320 | ONNX | yolo12l-320.onnx | ~101 MB |
| l (large) | 640 | ONNX | yolo12l-640.onnx | ~101 MB |
| l (large) | flexible | PT | yolo12l.pt | ~51 MB |
| x (xlarge) | 320 | ONNX | yolo12x-320.onnx | ~226 MB |
| x (xlarge) | 640 | ONNX | yolo12x-640.onnx | ~226 MB |
| x (xlarge) | flexible | PT | yolo12x.pt | ~114 MB |

## Model Selection Guide

### By Performance (Speed vs Accuracy)

- **nano (n)**: Fastest, lowest accuracy - ideal for edge devices
- **small (s)**: Good balance for most applications
- **medium (m)**: Better accuracy, moderate speed
- **large (l)**: High accuracy, slower
- **xlarge (x)**: Best accuracy, slowest - for high-end hardware

### By Format

#### ONNX (.onnx)
- **Pros**: Optimized for inference, cross-platform, faster
- **Cons**: Fixed input size (320 or 640)
- **Use when**: Production deployment, performance critical

#### PyTorch (.pt)
- **Pros**: Flexible input size, easy to modify, native PyTorch
- **Cons**: Slower than ONNX, requires PyTorch runtime
- **Use when**: Development, experimentation, custom input sizes

### By Version

- **YOLO11**: Stable, well-tested
- **YOLO12**: Latest features and improvements

## Configuration Examples

### Example 1: Fast Edge Processing (ONNX Nano 320)
```yaml
model_config:
  model_version: "12"
  model_variant: "n"
  input_size: 320
  model_format: "onnx"
  confidence: 0.5
```
**File used**: `yolo12n-320.onnx`

### Example 2: Balanced Production (ONNX Small 640)
```yaml
model_config:
  model_version: "12"
  model_variant: "s"
  input_size: 640
  model_format: "onnx"
  confidence: 0.5
```
**File used**: `yolo12s-640.onnx`

### Example 3: High Accuracy (ONNX Large 640)
```yaml
model_config:
  model_version: "12"
  model_variant: "l"
  input_size: 640
  model_format: "onnx"
  confidence: 0.5
```
**File used**: `yolo12l-640.onnx`

### Example 4: Development with Flexible Size (PyTorch)
```yaml
model_config:
  model_version: "12"
  model_variant: "m"
  input_size: 480
  model_format: "pt"
  confidence: 0.5
```
**File used**: `yolo12m.pt` (accepts any input size)

## Model Path Resolution

The system automatically resolves the model path based on:
1. `model_version` (11 or 12)
2. `model_variant` (n, s, m, l, x)
3. `input_size` (320, 640 for ONNX; any for PT)
4. `model_format` (onnx or pt)

**Pattern**: `yolo{version}{variant}-{size}.{format}` (ONNX) or `yolo{version}{variant}.{format}` (PT)

## Notes

- All models are pre-trained on COCO dataset (80 classes)
- ONNX models are pre-exported and optimized for inference
- PT models require Ultralytics library
- Input size for ONNX models must match the exported size (320 or 640)
- Input size for PT models is flexible (will be resized internally)

