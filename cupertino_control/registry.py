"""
CommandRegistry - Explicit command registration pattern

Bounded Context: Command registration and validation
Responsibilities:
  - Register commands with handlers
  - Validate command existence before execution
  - Provide introspection (available_commands, get_help)

Design Motivation (from Adeline):
  Problem: Optional callbacks make unclear which commands are available
  Solution: Explicit registration pattern

Threading: Thread-safe (uses lock for write operations)
Pattern: Registry with explicit registration
Inspiration: Adeline control/registry.py
"""

from typing import Dict, Callable, Set
import threading


class CommandNotAvailableError(Exception):
    """Raised when attempting to execute an unregistered command"""
    pass


class CommandRegistry:
    """
    Registry for MQTT commands with explicit registration.

    Key Features:
      - Fail-fast: Invalid commands rejected immediately
      - Introspection: Can query available commands at runtime
      - Type Safety: Handlers are strongly typed Callable objects
      - Self-Documenting: Each command has description

    Thread Safety:
      - Uses lock for write operations (register)
      - Read operations are lock-free (immutable dict reads)

    Example:
        registry = CommandRegistry()
        registry.register('pause', handler.pause, "Pauses processing")

        # Conditional registration
        if handler.supports_toggle:
            registry.register('toggle', handler.toggle, "Toggle feature")

        # Execute command
        try:
            registry.execute('pause')
        except CommandNotAvailableError as e:
            print(f"Command not available: {e}")
    """

    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}
        self._lock = threading.Lock()

    def register(self, command: str, handler: Callable, description: str) -> None:
        """
        Register a command with its handler function.

        Args:
            command: Command name (lowercase, no spaces)
            handler: Callable that executes the command
            description: Human-readable description for help text

        Raises:
            ValueError: If command already registered (double registration)

        Thread Safety: Uses lock for write operation
        """
        with self._lock:
            if command in self._commands:
                raise ValueError(f"Command '{command}' already registered")

            self._commands[command] = handler
            self._descriptions[command] = description

    def execute(self, command: str, command_data: dict = None) -> None:
        """
        Execute a registered command.

        Args:
            command: Command name to execute
            command_data: Optional command data (full JSON payload)

        Raises:
            CommandNotAvailableError: If command not registered

        Thread Safety: Read-only operation (no lock needed)
        """
        if command not in self._commands:
            raise CommandNotAvailableError(
                f"Command '{command}' not available. "
                f"Available commands: {', '.join(sorted(self.available_commands))}"
            )

        handler = self._commands[command]

        # Call handler with or without command_data
        if command_data is not None:
            handler(command_data)
        else:
            handler()

    def is_available(self, command: str) -> bool:
        """
        Check if command is registered.

        Thread Safety: Read-only operation (no lock needed)
        """
        return command in self._commands

    @property
    def available_commands(self) -> Set[str]:
        """
        Get set of all registered commands.

        Thread Safety: Read-only operation (no lock needed)
        Returns: Immutable set (snapshot)
        """
        return set(self._commands.keys())

    def get_help(self) -> Dict[str, str]:
        """
        Get dict of commands with descriptions.

        Thread Safety: Read-only operation (no lock needed)
        Returns: Immutable dict copy (snapshot)
        """
        return dict(self._descriptions)

    def count(self) -> int:
        """
        Get number of registered commands.

        Thread Safety: Read-only operation (no lock needed)
        """
        return len(self._commands)
