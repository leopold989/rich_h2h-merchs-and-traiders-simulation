class SimulatorError(Exception):
    """Base application error."""


class ConfigError(SimulatorError):
    """Raised when one of the JSON configs is invalid."""
