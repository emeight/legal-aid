# src/cmds/core.py

from selenium.webdriver.remote.webdriver import WebDriver
from typing import Callable, Dict, Union

from src.cmds.registry import lookup_command
from src.cmds.schema import get_param_specs, coerce_user_input


def prompt_for_args(fn: Callable) -> Dict[str, Union[str, bool, float]]:
    """Prompt user for arguments to the function.

    Parameter
    ---------
    fn : Callable
        Function to parse and format arguments for.
    
    Returns
    -------
    Dict[str, [str | bool | float]]
        Formatted function arguments.
    
    """
    # initialize output
    formatted_args = {}

    # get parameter specifications
    param_specs = get_param_specs(fn)

    # prompt user for each and coerce
    for param in param_specs:
        # prompt and format each argument
        user_input = input(f"{param.name} ({param.typ.__name__}): ")
        try:
            coerced_input = coerce_user_input(user_input, param.typ)
        except ValueError:
            # boolean not formatted correctly by user
            print('Please enter either "True" or "False"...\n')
            user_input = input(f"{param.name} ({param.typ.__name__}): ")
            coerced_input = coerce_user_input(user_input, param.typ)
        # add to result
        formatted_args[param.name] = coerced_input

    return formatted_args


def dispatch_command(driver: WebDriver, cmd: str) -> bool:
    """Lookup and execute a command if found.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    cmd : str
        Command string.

    Raises
    ------
    KeyError
        Raised from lookup_command.

    Returns
    -------
    bool
        True if command executed successfully.
    
    """
    command_fn = lookup_command(cmd)
    formatted_args = prompt_for_args(command_fn)

    # execute command
    try:
        command_fn(driver, **formatted_args)
        return True
    except Exception:
        return False
