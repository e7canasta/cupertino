#!/usr/bin/env python3
"""
Stream Processor Service - Entry Point
========================================

This script starts the Cupertino StreamProcessor service, which:
- Consumes RTSP video stream (via InferencePipeline)
- Performs YOLO object detection
- Monitors configured zones (polygon/line)
- Publishes detections and zone events to MQTT
- Responds to control commands via MQTT control plane

Usage:
    uv run python run_stream_processor.py --config config/cupertino_processor/processor_config.yaml

Architecture:
    - StreamProcessorService: Main orchestrator (cupertino_processor)
    - MQTTControlPlane: Command handler (cupertino_control)
    - DetectionPublisher: Publishes detection messages (cupertino_mqtt)
    - ZoneEventPublisher: Publishes zone event messages (cupertino_mqtt)

Lifecycle:
    1. Load configuration from YAML
    2. Setup logging (console + file)
    3. Create control plane and publishers
    4. Create StreamProcessorService
    5. Setup pipeline (load model, zones)
    6. Start service (non-blocking)
    7. Wait for stop signal (Ctrl+C or SIGTERM)
    8. Graceful shutdown

Signals:
    - SIGTERM: Graceful shutdown
    - SIGINT (Ctrl+C): Graceful shutdown

Logs:
    - Console: INFO level
    - File: logs/processor.log (INFO level)
"""

import argparse
import signal
import sys
import logging
from pathlib import Path
from typing import Optional

from cupertino_processor import StreamProcessorService
from cupertino_processor.config import ProcessorConfig
from cupertino_control import MQTTControlPlane
from cupertino_mqtt import DetectionPublisher, ZoneEventPublisher, create_logger


# ─────────────────────────────────────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging(log_file: Optional[Path] = None) -> logging.Logger:
    """
    Setup logging for the processor service.

    Args:
        log_file: Optional path to log file (default: logs/processor.log)

    Returns:
        Logger instance for the processor
    """
    # Create logs directory if needed
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Setup root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            *(
                [logging.FileHandler(log_file)]
                if log_file
                else []
            )
        ]
    )

    logger = logging.getLogger(__name__)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Main Service
# ─────────────────────────────────────────────────────────────────────────────

class ProcessorApp:
    """
    Main application wrapper for StreamProcessorService.

    Handles:
    - Configuration loading
    - Component initialization (control plane, publishers)
    - Signal handling (SIGTERM, SIGINT)
    - Graceful shutdown
    """

    def __init__(self, config_path: Path, log_file: Optional[Path] = None):
        """
        Initialize processor application.

        Args:
            config_path: Path to processor configuration YAML
            log_file: Optional path to log file
        """
        self.config_path = config_path
        self.log_file = log_file
        self.logger = setup_logging(log_file)

        # Components (initialized in setup())
        self.config: Optional[ProcessorConfig] = None
        self.control_plane: Optional[MQTTControlPlane] = None
        self.detection_publisher: Optional[DetectionPublisher] = None
        self.zone_event_publisher: Optional[ZoneEventPublisher] = None
        self.service: Optional[StreamProcessorService] = None

        # Signal handling
        self._shutdown_requested = False

    def setup(self):
        """
        Setup all components.

        Steps:
        1. Load configuration from YAML
        2. Create structured logger for MQTT publishers
        3. Create control plane
        4. Create publishers (detection, zone events)
        5. Create StreamProcessorService
        6. Setup pipeline (load model, zones)
        """
        self.logger.info("=" * 80)
        self.logger.info("🚀 Cupertino Stream Processor - Starting")
        self.logger.info("=" * 80)

        # 1. Load configuration
        self.logger.info(f"📄 Loading configuration: {self.config_path}")
        self.config = ProcessorConfig.from_yaml(self.config_path)
        self.logger.info(f"✅ Configuration loaded (service_id={self.config.service_id})")

        # 2. Create structured logger for publishers
        mqtt_logger = create_logger(component="mqtt_publisher")

        # 3. Create control plane
        self.logger.info("🔌 Creating MQTT control plane")
        self.control_plane = MQTTControlPlane(
            broker_host=self.config.mqtt_config.broker,
            broker_port=self.config.mqtt_config.port,
            command_topic=f"cupertino/control/{self.config.service_id}/commands",
            status_topic=f"cupertino/control/{self.config.service_id}/status",
            client_id=f"processor_{self.config.service_id}",
            username=self.config.mqtt_config.username,
            password=self.config.mqtt_config.password,
        )
        self.logger.info("✅ Control plane created")

        # 4. Create publishers
        self.logger.info("📤 Creating MQTT publishers")

        # Detection publisher
        detection_topic = self.config.mqtt_config.detection_topic.format(
            service_id=self.config.service_id
        )
        self.detection_publisher = DetectionPublisher(
            broker_host=self.config.mqtt_config.broker,
            broker_port=self.config.mqtt_config.port,
            topic=detection_topic,
            logger=mqtt_logger,
            client_id=f"publisher_detections_{self.config.service_id}",
            username=self.config.mqtt_config.username,
            password=self.config.mqtt_config.password,
            qos=self.config.mqtt_config.qos,
        )

        # Zone event publisher
        zone_event_topic = self.config.mqtt_config.zone_event_topic.format(
            service_id=self.config.service_id
        )
        self.zone_event_publisher = ZoneEventPublisher(
            broker_host=self.config.mqtt_config.broker,
            broker_port=self.config.mqtt_config.port,
            topic=zone_event_topic,
            logger=mqtt_logger,
            client_id=f"publisher_zones_{self.config.service_id}",
            username=self.config.mqtt_config.username,
            password=self.config.mqtt_config.password,
            qos=self.config.mqtt_config.qos,
        )

        self.logger.info(f"  - Detection topic: {detection_topic}")
        self.logger.info(f"  - Zone event topic: {zone_event_topic}")
        self.logger.info("✅ Publishers created")

        # 5. Create StreamProcessorService
        self.logger.info("🏗️  Creating stream processor service")
        self.service = StreamProcessorService(
            config=self.config,
            control_plane=self.control_plane,
            detection_publisher=self.detection_publisher,
            zone_event_publisher=self.zone_event_publisher,
        )
        self.logger.info("✅ Service created")

        # 6. Setup pipeline
        self.logger.info("⚙️  Setting up inference pipeline")
        self.service.setup()
        self.logger.info("✅ Pipeline setup complete")

        self.logger.info("=" * 80)

    def run(self):
        """
        Run the processor service.

        Blocks until shutdown is requested (via signal or exception).
        """
        if not self.service:
            raise RuntimeError("Service not initialized. Call setup() first.")

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # Start service (non-blocking)
            self.service.start()

            self.logger.info("✅ Service started successfully")
            self.logger.info("Press Ctrl+C to stop")
            self.logger.info("=" * 80)

            # Block until stopped
            self.service.wait()

        except KeyboardInterrupt:
            self.logger.info("\n⚠️  KeyboardInterrupt received")
            self.shutdown()

        except Exception as e:
            self.logger.error(f"❌ Service error: {e}", exc_info=True)
            self.shutdown()
            sys.exit(1)

    def shutdown(self):
        """
        Graceful shutdown of all components.

        Order:
        1. Stop service (pipeline, publishers)
        2. Disconnect control plane
        3. Log completion
        """
        if self._shutdown_requested:
            self.logger.warning("⚠️  Shutdown already in progress")
            return

        self._shutdown_requested = True

        self.logger.info("=" * 80)
        self.logger.info("🛑 Shutting down processor service")
        self.logger.info("=" * 80)

        # Stop service (if running)
        if self.service:
            try:
                self.service.stop()
                self.logger.info("✅ Service stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping service: {e}")

        # Disconnect control plane (if connected)
        if self.control_plane:
            try:
                self.control_plane.disconnect()
                self.logger.info("✅ Control plane disconnected")
            except Exception as e:
                self.logger.error(f"❌ Error disconnecting control plane: {e}")

        self.logger.info("=" * 80)
        self.logger.info("✅ Shutdown complete")
        self.logger.info("=" * 80)

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGTERM, SIGINT).

        Args:
            signum: Signal number
            frame: Current stack frame (unused)
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"\n⚠️  Received signal {signal_name} ({signum})")
        self.shutdown()
        sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Cupertino Stream Processor - RTSP + YOLO + MQTT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default config
  uv run python run_stream_processor.py --config config/cupertino_processor/processor_config.yaml

  # Start with custom log file
  uv run python run_stream_processor.py --config config/cupertino_processor/processor_config.yaml --log-file logs/custom.log

  # Start without file logging (console only)
  uv run python run_stream_processor.py --config config/cupertino_processor/processor_config.yaml --no-log-file

For more information, see: README.md
        """
    )

    parser.add_argument(
        '--config',
        type=Path,
        required=True,
        help='Path to processor configuration YAML file'
    )

    parser.add_argument(
        '--log-file',
        type=Path,
        default=Path('logs/processor.log'),
        help='Path to log file (default: logs/processor.log)'
    )

    parser.add_argument(
        '--no-log-file',
        action='store_true',
        help='Disable file logging (console only)'
    )

    return parser.parse_args()


def main():
    """
    Main entry point.

    Workflow:
    1. Parse CLI arguments
    2. Create ProcessorApp
    3. Setup components
    4. Run service (blocks until stopped)
    """
    args = parse_args()

    # Determine log file
    log_file = None if args.no_log_file else args.log_file

    # Validate config file exists
    if not args.config.exists():
        print(f"❌ Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    # Create and run app
    app = ProcessorApp(
        config_path=args.config,
        log_file=log_file
    )

    try:
        app.setup()
        app.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
