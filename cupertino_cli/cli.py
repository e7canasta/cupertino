"""
Cupertino CLI - Main entry point.

Provides command-line interface for sending MQTT commands to StreamProcessor.
"""

import argparse
import yaml
import sys
from pathlib import Path
from typing import Dict, Any

from .mqtt_client import MQTTCommandClient


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML file

    Returns:
        Dictionary with command configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is invalid
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")


def send_command(
    command: Dict[str, Any],
    service_id: str = "cam_01",
    broker: str = "localhost",
    port: int = 1883
) -> None:
    """
    Send command to StreamProcessor via MQTT.

    Args:
        command: Command dictionary
        service_id: Target service ID
        broker: MQTT broker host
        port: MQTT broker port
    """
    topic = f"cupertino/control/{service_id}/commands"

    client = MQTTCommandClient(broker=broker, port=port)
    client.send_command(topic, command, qos=1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cupertino CLI - Send MQTT commands to StreamProcessor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add zone from YAML config
  cupertino-cli add-zone config/commands/add_zone_entrance.yaml

  # Remove zone by ID
  cupertino-cli remove-zone entrance

  # Enable/disable zone
  cupertino-cli enable-zone entrance
  cupertino-cli disable-zone entrance

  # Change YOLO model
  cupertino-cli set-model config/commands/set_model.yaml

  # Simple commands (no arguments)
  cupertino-cli pause
  cupertino-cli resume
  cupertino-cli status
  cupertino-cli health
  cupertino-cli list-zones
"""
    )

    # Global arguments
    parser.add_argument(
        "--service-id",
        default="cam_01",
        help="Target service ID (default: cam_01)"
    )
    parser.add_argument(
        "--broker",
        default="localhost",
        help="MQTT broker host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # add-zone command
    add_zone = subparsers.add_parser('add-zone', help='Add zone from YAML config')
    add_zone.add_argument('config', help='Path to zone config YAML')

    # remove-zone command
    remove_zone = subparsers.add_parser('remove-zone', help='Remove zone by ID')
    remove_zone.add_argument('zone_id', help='Zone ID to remove')

    # enable-zone command
    enable_zone = subparsers.add_parser('enable-zone', help='Enable zone by ID')
    enable_zone.add_argument('zone_id', help='Zone ID to enable')

    # disable-zone command
    disable_zone = subparsers.add_parser('disable-zone', help='Disable zone by ID')
    disable_zone.add_argument('zone_id', help='Zone ID to disable')

    # set-model command
    set_model = subparsers.add_parser('set-model', help='Change YOLO model from YAML config')
    set_model.add_argument('config', help='Path to model config YAML')

    # Simple commands (no arguments)
    subparsers.add_parser('pause', help='Pause stream processing')
    subparsers.add_parser('resume', help='Resume stream processing')
    subparsers.add_parser('status', help='Query service status')
    subparsers.add_parser('health', help='Health check')
    subparsers.add_parser('list-zones', help='List active zones')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == 'add-zone':
            config = load_yaml_config(args.config)
            send_command(config, args.service_id, args.broker, args.port)

        elif args.command == 'remove-zone':
            command = {
                'command': 'remove_zone',
                'zone_id': args.zone_id
            }
            send_command(command, args.service_id, args.broker, args.port)

        elif args.command == 'enable-zone':
            command = {
                'command': 'enable_zone',
                'zone_id': args.zone_id
            }
            send_command(command, args.service_id, args.broker, args.port)

        elif args.command == 'disable-zone':
            command = {
                'command': 'disable_zone',
                'zone_id': args.zone_id
            }
            send_command(command, args.service_id, args.broker, args.port)

        elif args.command == 'set-model':
            config = load_yaml_config(args.config)
            send_command(config, args.service_id, args.broker, args.port)

        elif args.command in ['pause', 'resume', 'status', 'health', 'list-zones']:
            command = {'command': args.command}
            send_command(command, args.service_id, args.broker, args.port)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
