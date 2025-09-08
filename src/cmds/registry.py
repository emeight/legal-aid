# src/cmds/registry.py

from typing import Callable, Dict

from src.cmds.schema import CommandSpec
from src.cmds.impl.surf import access_url


COMMAND_REGISTRY: Dict[str, CommandSpec] = {
    "OPEN_URL": access_url
}


def lookup_command(cmd: str) -> Callable:
    """Lookup a command in the registry and return the corresponding function, if it exists.

    Parameters
    ----------
    cmd : str
        Command string to lookup in registry.

    Returns
    -------
    Callable
        The function corresponding to the command.
    
    """
    return COMMAND_REGISTRY[cmd.upper()]