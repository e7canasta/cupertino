# Cupertino CLI

Command-line interface for sending MQTT commands to Cupertino StreamProcessor service.

## Installation

The CLI is installed automatically when you install the `cupertino` package:

```bash
uv pip install -e .
```

This creates a `cupertino-cli` command in your virtual environment.

## Usage

### Basic Commands

```bash
# Health check
uv run cupertino-cli health

# Query service status
uv run cupertino-cli status

# List active zones
uv run cupertino-cli list-zones

# Pause/resume processing
uv run cupertino-cli pause
uv run cupertino-cli resume
```

### Zone Management

#### Add Zone (from YAML config)

```bash
uv run cupertino-cli add-zone scripts/commands/add_zone_entrance.yaml
```

Example YAML (`scripts/commands/add_zone_entrance.yaml`):
```yaml
command: add_zone
zone_id: entrance
zone_type: polygon
coordinates:
  - [100, 200]
  - [500, 200]
  - [500, 600]
  - [100, 600]
enabled: true
```

#### Remove Zone

```bash
uv run cupertino-cli remove-zone entrance
```

#### Enable/Disable Zone

```bash
uv run cupertino-cli enable-zone entrance
uv run cupertino-cli disable-zone entrance
```

### Model Configuration

Change YOLO model variant (from YAML config):

```bash
uv run cupertino-cli set-model scripts/commands/set_model_yolov8s.yaml
```

Example YAML (`scripts/commands/set_model_yolov8s.yaml`):
```yaml
command: set_model
model_variant: "s"
input_size: 640
confidence: 0.5
iou_threshold: 0.5
```

### Global Options

```bash
# Target specific service ID (default: cam_01)
uv run cupertino-cli --service-id cam_02 status

# Use different MQTT broker
uv run cupertino-cli --broker 192.168.1.100 --port 1883 status
```

## Makefile Integration

The CLI is integrated into the Makefile for convenience:

```bash
# Add zones
make add-zone-entrance
make add-zone-exit
make add-zone-crossing

# Control commands
make pause
make resume
make health
make list-zones
```

## Architecture

```
cupertino_cli/
├── __init__.py       # Package metadata
├── cli.py            # Main CLI entry point (argparse)
├── mqtt_client.py    # MQTT client wrapper
└── README.md         # This file
```

### Components

- **cli.py**: Argument parsing and command dispatching
- **mqtt_client.py**: MQTT connection and message publishing

### MQTT Topics

Commands are published to:
```
cupertino/control/{service_id}/commands
```

With QoS 1 (at least once delivery) for reliability.

## Examples

### Full Workflow

```bash
# 1. Start services
make start

# 2. Check status
uv run cupertino-cli health

# 3. Add zones
make add-zone-entrance
make add-zone-exit

# 4. Monitor events (in separate terminal)
make monitor-zones

# 5. Pause processing
make pause

# 6. Resume processing
make resume

# 7. Stop services
make stop
```

### Monitoring MQTT

You can monitor MQTT messages directly:

```bash
# Watch control commands
mosquitto_sub -t "cupertino/control/cam_01/commands" -v

# Watch service status
mosquitto_sub -t "cupertino/control/cam_01/status" -v

# Watch all cupertino topics
mosquitto_sub -t "cupertino/#" -v
```

## Error Handling

The CLI provides clear error messages:

```bash
# Broker not running
❌ Error: Unable to connect to MQTT broker at localhost:1883. Is mosquitto running?

# Invalid config file
❌ Error: Config file not found: scripts/commands/invalid.yaml

# Invalid YAML
❌ Error: Invalid YAML in scripts/commands/bad.yaml: ...
```

## Dependencies

- `paho-mqtt>=1.6.1` - MQTT client library
- `pyyaml>=6.0` - YAML parsing

## Design Decisions

### Why YAML configs?

- **Readability**: Easy to understand zone definitions
- **Reusability**: Same config can be reused across sessions
- **Version control**: Zone configs can be committed to git
- **Less error-prone**: No manual JSON writing

### Why QoS 1 for commands?

Control plane commands use QoS 1 (at least once) to ensure reliability:
- Critical commands (add_zone, set_model) must be delivered
- Data plane (detections, zones) uses QoS 0 for throughput

### Why separate from main packages?

The CLI is a thin wrapper around MQTT publishing:
- No business logic (just message formatting)
- Independent from processor implementation
- Easy to test without running full system

## Testing

Test the CLI without a running processor:

```bash
# Start MQTT broker
mosquitto -v

# Subscribe to commands topic
mosquitto_sub -t "cupertino/control/cam_01/commands" -v

# In another terminal, send command
uv run cupertino-cli health

# You should see the JSON message in the subscriber terminal
```

Expected output in subscriber:
```json
cupertino/control/cam_01/commands {"command": "health"}
```

## Troubleshooting

### Command not found: cupertino-cli

Make sure you've installed the package:
```bash
uv pip install -e .
```

And use `uv run`:
```bash
uv run cupertino-cli --help
```

### Connection refused

Make sure mosquitto is running:
```bash
systemctl status mosquitto
# Or
mosquitto -v
```

### No response from processor

The CLI only sends commands, it doesn't wait for responses. To see processor responses:

1. Monitor status topic:
```bash
make monitor-status
```

2. Check processor logs:
```bash
make logs
```

## Future Enhancements

- [ ] Add `--wait` flag to wait for status response
- [ ] Add `--json` flag for JSON output (machine-readable)
- [ ] Add command history/replay
- [ ] Add batch command execution (from file)
- [ ] Add shell completion (bash/zsh)

---

**Version**: 1.0.0
**Authors**: Ernesto (Visiona) + Gaby
**Philosophy**: "Simple para leer, NO simple para escribir una vez"
