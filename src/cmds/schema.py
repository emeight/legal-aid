# src/cmds/schema.py

from dataclasses import dataclass
import inspect
from types import UnionType
from typing import Annotated, Any, Callable, List, Protocol, get_args, get_origin, get_type_hints
from selenium.webdriver.remote.webdriver import WebDriver

# --- type defs ---

UserInput = str | float | bool


# --- protocols ---

class CommandFunc(Protocol):
    """Protocol for static tooling."""
    def __call__(self, driver: WebDriver, *args: UserInput) -> None:
        ...


# --- dataclasses ---

@dataclass(frozen=True)
class CommandSpec:
    """Runtime description of a command."""
    fn: CommandFunc
    arg_types: tuple[type, ...]
    exec_msg: str = ""


@dataclass(frozen=True)
class ArgSpec:
    """Runtime description of a single parameter to prompt for."""
    name: str
    typ: type            # one of (str, float, bool)
    has_default: bool
    default: Any
    is_varargs: bool     # True if this is *args


# --- functions ---

_ALLOWED = (str, float, bool)


def _unwrap_annotated(tp: Any) -> Any:
    return get_args(tp)[0] if get_origin(tp) is Annotated else tp


def _resolve_user_input_type(ann: Any) -> type:
    """Map an annotation to one of (str, float, bool). Defaults to str if unknown."""
    ann = _unwrap_annotated(ann)

    if ann is inspect._empty:
        return str
    if ann in _ALLOWED:
        return ann

    origin = get_origin(ann)
    if origin is UnionType:
        for a in get_args(ann):
            a = _unwrap_annotated(a)
            if a is type(None):  # Optional[T] -> skip None
                continue
            if a in _ALLOWED:
                return a
        return str

    return str


def get_param_specs(fn: Callable[..., Any]) -> List[ArgSpec]:
    """Inspect a command function and return promptable parameter specs (excluding `driver`)."""
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)

    params = list(sig.parameters.values())
    if not params:
        return []

    # assume first param is the driver
    prompt_params: List[inspect.Parameter] = params[1:]

    specs: List[ArgSpec] = []
    for p in prompt_params:
        if p.kind == inspect.Parameter.VAR_POSITIONAL:  # *args
            ann = hints.get(p.name, p.annotation)
            base = _resolve_user_input_type(ann)
            specs.append(ArgSpec(name=p.name, typ=base, has_default=False, default=None, is_varargs=True))
        elif p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            ann = hints.get(p.name, p.annotation)
            base = _resolve_user_input_type(ann)
            has_def = p.default is not inspect._empty
            default = p.default if has_def else None
            specs.append(ArgSpec(name=p.name, typ=base, has_default=has_def, default=default, is_varargs=False))
        else:
            # skip keyword-only or **kwargs for a simple CLI; you can extend if you need them.
            raise TypeError(f"Unsupported parameter kind for '{p.name}': {p.kind}")
    return specs


def coerce_user_input(s: str, typ: type) -> UserInput:
    """Coerce user input string into correct type.

    Parameters
    ----------
    s : str
        User input string.
    
    type : type
        Type to coerce to.

    Raises
    ------
    TypeError
        Raised when the input type is not one of (str, float, bool).

    ValueError
        Raised when the input string is not "True" or "False" despite the type being specified as boolean.
    
    """
    if typ is str:
        return s
    if typ is float:
        return float(s)
    if typ is bool:
        if s.lower() == "true":
            return True
        elif s.lower() == "false":
            return False
        else:
            val_err_msg = f"Expected True or False, but got: {s}"
            raise ValueError(val_err_msg)
    type_err_msg = f"Unsupported type {typ}"
    raise TypeError(type_err_msg)