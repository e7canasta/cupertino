# go2rtc Configuration

## Purpose

Converts video files to RTSP streams for testing the Cupertino StreamProcessor without needing real cameras.

## Installation

### Option 1: Binary (Recommended)

Download from releases: https://github.com/AlexxIT/go2rtc/releases

```bash
# Linux/macOS
wget https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_amd64
chmod +x go2rtc_linux_amd64
sudo mv go2rtc_linux_amd64 /usr/local/bin/go2rtc
```

### Option 2: Docker

```bash
docker run -p 1984:1984 -p 8554:8554 \
  -v $(pwd)/config/go2rtc:/config \
  -v $(pwd)/data:/data \
  alexxit/go2rtc
```

## Usage

### Start go2rtc

```bash
go2rtc -config config/go2rtc/go2rtc.yaml
```

### Health Check

```bash
# Check API is running
curl http://localhost:1984/api/streams

# Expected output:
# {"camera1": {...}}
```

### Test Stream

```bash
# Option 1: ffplay (if installed)
ffplay rtsp://localhost:8554/camera1

# Option 2: VLC
vlc rtsp://localhost:8554/camera1

# Option 3: Open in browser
# http://localhost:1984/
```

## Configuration

### Stream Configuration

```yaml
streams:
  camera1:
    - ffmpeg:data/videos/vehicles-1280x720.mp4#video=h264#audio=none#hardware
```

**Options**:
- `video=h264`: Force H.264 codec (compatible with RTSP clients)
- `audio=none`: No audio track (reduces overhead)
- `hardware`: Use hardware acceleration if available (faster encoding)

### Ports

- **1984**: Web UI and API
- **8554**: RTSP server

### Video File Requirements

Place your test video at:
```
data/videos/vehicles-1280x720.mp4
```

**Recommended specs**:
- Resolution: 1280x720 (or lower for faster processing)
- Codec: H.264
- Frame rate: 25-30 FPS

## Troubleshooting

### Stream not available

Check if video file exists:
```bash
ls -lh data/videos/vehicles-1280x720.mp4
```

### Port already in use

Change ports in `go2rtc.yaml`:
```yaml
api:
  listen: ":1985"  # Changed from 1984
rtsp:
  listen: ":8555"  # Changed from 8554
```

### High CPU usage

Disable hardware acceleration:
```yaml
streams:
  camera1:
    - ffmpeg:data/videos/vehicles-1280x720.mp4#video=h264#audio=none
```

## Integration with Cupertino

### Processor Config

Update `config/cupertino_processor/processor_config.yaml`:

```yaml
rtsp_url: "rtsp://localhost:8554/camera1"
max_fps: 25
```

### Testing Flow

1. Start go2rtc: `go2rtc -config config/go2rtc/go2rtc.yaml`
2. Start processor: `uv run python run_stream_processor.py --config config/cupertino_processor/processor_config.yaml`
3. Monitor detections: `mosquitto_sub -t "cupertino/data/detections/#"`

## References

- go2rtc GitHub: https://github.com/AlexxIT/go2rtc
- RTSP Protocol: https://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol
