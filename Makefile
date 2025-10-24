# ============================================================
# Cupertino Testing Environment - Makefile
# ============================================================
# Version: 1.0
# Authors: Ernesto (Visiona) + Gaby
# Philosophy: "Simple para leer, NO simple para escribir una vez"
# ============================================================

.PHONY: help start stop restart status clean logs setup
.PHONY: start-mosquitto start-go2rtc start-processor
.PHONY: stop-go2rtc stop-processor
.PHONY: run-processor run-go2rtc
.PHONY: monitor-detections monitor-zones monitor-status monitor-commands monitor-all
.PHONY: add-zone-entrance add-zone-exit add-zone-crossing pause resume health list-zones

# ============================================================
# Configuration
# ============================================================

SERVICE_ID := cam_01
CONFIG_FILE := config/cupertino_processor/processor_config.yaml
GO2RTC_CONFIG := config/go2rtc/go2rtc.yaml
LOGS_DIR := logs

# MQTT Topics
MQTT_DETECTIONS := cupertino/data/detections/$(SERVICE_ID)
MQTT_ZONES := cupertino/data/zones/$(SERVICE_ID)
MQTT_STATUS := cupertino/control/$(SERVICE_ID)/status
MQTT_COMMANDS := cupertino/control/$(SERVICE_ID)/commands

# PID files
GO2RTC_PID := .go2rtc.pid
PROCESSOR_PID := .processor.pid

# ============================================================
# Default Target
# ============================================================

help:
	@echo "Cupertino Testing Environment"
	@echo "=============================="
	@echo ""
	@echo "Lifecycle:"
	@echo "  make start          - Start all services (go2rtc + processor)"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make status         - Check services status"
	@echo ""
	@echo "Development (foreground):"
	@echo "  make run-processor  - Run processor in foreground (see logs in terminal)"
	@echo "  make run-go2rtc     - Run go2rtc in foreground (see logs in terminal)"
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitor-detections  - Monitor YOLO detections"
	@echo "  make monitor-zones       - Monitor zone events"
	@echo "  make monitor-status      - Monitor service status"
	@echo "  make monitor-commands    - Monitor control commands"
	@echo "  make monitor-all         - Monitor all MQTT topics"
	@echo ""
	@echo "Commands:"
	@echo "  make add-zone-entrance   - Add entrance zone"
	@echo "  make add-zone-exit       - Add exit zone"
	@echo "  make add-zone-crossing   - Add crossing line zone"
	@echo "  make pause               - Pause processing"
	@echo "  make resume              - Resume processing"
	@echo "  make health              - Health check"
	@echo "  make list-zones          - List active zones"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Clean temporary files"
	@echo "  make logs           - Show recent processor logs"
	@echo "  make setup          - Setup environment (first-time only)"

# ============================================================
# Lifecycle Commands
# ============================================================

start: setup start-mosquitto start-go2rtc start-processor
	@echo ""
	@echo "✅ All services started"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  make monitor-detections  # Watch detections"
	@echo "  make monitor-zones       # Watch zone events"
	@echo "  make monitor-status      # Watch service status"
	@echo ""
	@echo "🎮 Commands:"
	@echo "  make add-zone-entrance   # Add entrance zone"
	@echo "  make pause               # Pause processing"
	@echo "  make health              # Health check"
	@echo ""

stop: stop-processor stop-go2rtc
	@echo "✅ All services stopped"

restart: stop start

# ============================================================
# Individual Service Commands
# ============================================================

start-mosquitto:
	@echo "🔌 Checking mosquitto..."
	@if systemctl is-active --quiet mosquitto; then \
		echo "✅ mosquitto already running"; \
	else \
		echo "⚠️  mosquitto not running (expected to be running)"; \
		echo "    Please start it manually: sudo systemctl start mosquitto"; \
		exit 1; \
	fi

start-go2rtc:
	@if [ -f $(GO2RTC_PID) ] && kill -0 $$(cat $(GO2RTC_PID)) 2>/dev/null; then \
		echo "✅ go2rtc already running (PID: $$(cat $(GO2RTC_PID)))"; \
	else \
		echo "🎥 Starting go2rtc..."; \
		go2rtc -config $(GO2RTC_CONFIG) > $(LOGS_DIR)/go2rtc.log 2>&1 & \
		echo $$! > $(GO2RTC_PID); \
		sleep 2; \
		if kill -0 $$(cat $(GO2RTC_PID)) 2>/dev/null; then \
			echo "✅ go2rtc running (PID: $$(cat $(GO2RTC_PID)))"; \
			echo "   Stream: rtsp://localhost:8554/camera1"; \
			echo "   Web UI: http://localhost:1984"; \
		else \
			echo "❌ go2rtc failed to start (check $(LOGS_DIR)/go2rtc.log)"; \
			rm -f $(GO2RTC_PID); \
			exit 1; \
		fi; \
	fi

start-processor:
	@if [ -f $(PROCESSOR_PID) ] && kill -0 $$(cat $(PROCESSOR_PID)) 2>/dev/null; then \
		echo "✅ Stream processor already running (PID: $$(cat $(PROCESSOR_PID)))"; \
	else \
		echo "🔧 Starting stream processor..."; \
		uv run python run_stream_processor.py --config $(CONFIG_FILE) > $(LOGS_DIR)/processor.log 2>&1 & \
		echo $$! > $(PROCESSOR_PID); \
		sleep 3; \
		if kill -0 $$(cat $(PROCESSOR_PID)) 2>/dev/null; then \
			echo "✅ Stream processor running (PID: $$(cat $(PROCESSOR_PID)))"; \
			echo "   Service ID: $(SERVICE_ID)"; \
			echo "   Config: $(CONFIG_FILE)"; \
		else \
			echo "❌ Stream processor failed to start (check $(LOGS_DIR)/processor.log)"; \
			rm -f $(PROCESSOR_PID); \
			exit 1; \
		fi; \
	fi

stop-go2rtc:
	@if [ -f $(GO2RTC_PID) ]; then \
		echo "🛑 Stopping go2rtc..."; \
		kill $$(cat $(GO2RTC_PID)) 2>/dev/null || true; \
		rm -f $(GO2RTC_PID); \
		sleep 1; \
		echo "✅ go2rtc stopped"; \
	else \
		echo "⚠️  go2rtc not running"; \
	fi

stop-processor:
	@if [ -f $(PROCESSOR_PID) ]; then \
		echo "🛑 Stopping stream processor..."; \
		kill $$(cat $(PROCESSOR_PID)) 2>/dev/null || true; \
		rm -f $(PROCESSOR_PID); \
		sleep 1; \
		echo "✅ Stream processor stopped"; \
	else \
		echo "⚠️  Stream processor not running"; \
	fi

status:
	@echo "Service Status:"
	@echo "  mosquitto: $$(systemctl is-active mosquitto 2>/dev/null || echo 'inactive')"
	@if [ -f $(GO2RTC_PID) ] && kill -0 $$(cat $(GO2RTC_PID)) 2>/dev/null; then \
		echo "  go2rtc: running (PID: $$(cat $(GO2RTC_PID)))"; \
	else \
		echo "  go2rtc: stopped"; \
	fi
	@if [ -f $(PROCESSOR_PID) ] && kill -0 $$(cat $(PROCESSOR_PID)) 2>/dev/null; then \
		echo "  processor: running (PID: $$(cat $(PROCESSOR_PID)))"; \
	else \
		echo "  processor: stopped"; \
	fi

# ============================================================
# Development Commands (Foreground)
# ============================================================

run-processor:
	@echo "🔧 Running stream processor in foreground (Ctrl+C to stop)..."
	@echo "   Config: $(CONFIG_FILE)"
	@echo "   Service ID: $(SERVICE_ID)"
	@echo ""
	@uv run python run_stream_processor.py --config $(CONFIG_FILE)

run-go2rtc:
	@echo "🎥 Running go2rtc in foreground (Ctrl+C to stop)..."
	@echo "   Config: $(GO2RTC_CONFIG)"
	@echo "   Stream: rtsp://localhost:8554/camera1"
	@echo "   Web UI: http://localhost:1984"
	@echo ""
	@go2rtc -config $(GO2RTC_CONFIG)

# ============================================================
# Monitoring Commands
# ============================================================

monitor-detections:
	@echo "📊 Monitoring detections (Ctrl+C to stop)..."
	@mosquitto_sub -t "$(MQTT_DETECTIONS)" -v

monitor-zones:
	@echo "📊 Monitoring zone events (Ctrl+C to stop)..."
	@mosquitto_sub -t "$(MQTT_ZONES)" -v

monitor-status:
	@echo "📊 Monitoring service status (Ctrl+C to stop)..."
	@mosquitto_sub -t "$(MQTT_STATUS)" -v

monitor-commands:
	@echo "📊 Monitoring control commands (Ctrl+C to stop)..."
	@mosquitto_sub -t "$(MQTT_COMMANDS)" -v

monitor-all:
	@echo "📊 Monitoring all topics (Ctrl+C to stop)..."
	@mosquitto_sub -t "cupertino/#" -v

# ============================================================
# Command Shortcuts
# ============================================================

add-zone-entrance:
	@echo "➕ Adding entrance zone..."
	@uv run cupertino-cli add-zone scripts/commands/add_zone_entrance.yaml

add-zone-exit:
	@echo "➕ Adding exit zone..."
	@uv run cupertino-cli add-zone scripts/commands/add_zone_exit.yaml

add-zone-crossing:
	@echo "➕ Adding crossing line zone..."
	@uv run cupertino-cli add-zone scripts/commands/add_zone_crossing_line.yaml

pause:
	@echo "⏸️  Pausing stream processing..."
	@uv run cupertino-cli pause

resume:
	@echo "▶️  Resuming stream processing..."
	@uv run cupertino-cli resume

health:
	@echo "🏥 Health check..."
	@uv run cupertino-cli health

list-zones:
	@echo "📋 Listing zones..."
	@uv run cupertino-cli list-zones

# ============================================================
# Cleanup
# ============================================================

clean:
	@echo "🧹 Cleaning temporary files..."
	@rm -f $(GO2RTC_PID) $(PROCESSOR_PID)
	@rm -f $(LOGS_DIR)/*.log
	@echo "✅ Clean complete"

logs:
	@if [ -f $(LOGS_DIR)/processor.log ]; then \
		echo "📋 Recent processor logs (last 50 lines):"; \
		echo ""; \
		tail -n 50 $(LOGS_DIR)/processor.log; \
	else \
		echo "⚠️  No processor logs found"; \
	fi

# ============================================================
# Setup (first-time only)
# ============================================================

setup:
	@mkdir -p $(LOGS_DIR)
	@mkdir -p config/go2rtc
	@mkdir -p config/cupertino_processor
	@mkdir -p config/commands
	@if [ ! -f $(CONFIG_FILE) ]; then \
		echo "⚠️  Config file not found: $(CONFIG_FILE)"; \
		exit 1; \
	fi
	@if [ ! -f $(GO2RTC_CONFIG) ]; then \
		echo "⚠️  go2rtc config not found: $(GO2RTC_CONFIG)"; \
		exit 1; \
	fi
