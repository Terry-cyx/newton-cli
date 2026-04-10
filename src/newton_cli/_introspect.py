"""Allow-list-driven public-symbol walker for Newton.

We never import from `newton._src.*`. The CLI's view of "public" is exactly the
union of `dir()` (excluding underscored names) on the modules listed in
`PUBLIC_MODULES`.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Iterable

PUBLIC_MODULES: tuple[str, ...] = (
    "newton",
    "newton.geometry",
    "newton.solvers",
    "newton.sim",
    "newton.ik",
    "newton.sensors",
    "newton.usd",
    "newton.viewer",
    "newton.utils",
    "newton.math",
    "newton.examples",
)

PRIVATE_MARKER = "_src"


class PrivateModuleError(ValueError):
    """Raised when a caller tries to inspect anything under newton._src."""


@dataclass(frozen=True)
class Symbol:
    name: str
    module: str
    kind: str
    summary: str

    def to_dict(self) -> dict:
        return {"name": self.name, "module": self.module, "kind": self.kind, "summary": self.summary}


def assert_public(module_name: str) -> None:
    """Reject any path that touches newton._src.* (even as a substring)."""
    if PRIVATE_MARKER in module_name.split("."):
        raise PrivateModuleError(
            f"refusing to inspect private module '{module_name}': "
            f"newton._src is not part of the public API"
        )


def _kind_of(obj: Any) -> str:
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        return "function"
    if inspect.ismodule(obj):
        return "module"
    return "value"


def _summary(obj: Any) -> str:
    doc = inspect.getdoc(obj) or ""
    return doc.strip().split("\n", 1)[0] if doc else ""


def _public_names(module: Any) -> Iterable[str]:
    for name in dir(module):
        if name.startswith("_"):
            continue
        yield name


def list_symbols(module_name: str | None = None) -> list[Symbol]:
    """List public symbols across the allow-list, or filtered to one module."""
    if module_name is not None:
        assert_public(module_name)
        if module_name not in PUBLIC_MODULES:
            raise PrivateModuleError(
                f"module '{module_name}' is not in the public allow-list. "
                f"Allowed: {', '.join(PUBLIC_MODULES)}"
            )
        modules = (module_name,)
    else:
        modules = PUBLIC_MODULES

    out: list[Symbol] = []
    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        for name in _public_names(mod):
            try:
                obj = getattr(mod, name)
            except AttributeError:
                continue
            # Skip submodules re-exposed at top level — they get walked on their own.
            if inspect.ismodule(obj) and obj.__name__ in PUBLIC_MODULES:
                continue
            out.append(
                Symbol(
                    name=name,
                    module=mod_name,
                    kind=_kind_of(obj),
                    summary=_summary(obj),
                )
            )
    return out


def resolve_symbol(dotted: str) -> tuple[str, str, Any]:
    """Resolve a dotted name like 'geometry.GeoType' or 'ModelBuilder' to (module, name, obj).

    Search order:
      1. If the dotted path starts with one of PUBLIC_MODULES (or its short tail),
         try that module first.
      2. Otherwise, try every public module and return the first hit.
    """
    assert_public(dotted)

    if "." in dotted:
        head, _, tail = dotted.rpartition(".")
        # Try as fully-qualified `newton.<head>` first
        candidates = [f"newton.{head}", head]
    else:
        head = ""
        tail = dotted
        candidates = []

    # Always also probe every public module for the bare name.
    candidates.extend(PUBLIC_MODULES)

    seen = set()
    for mod_name in candidates:
        if mod_name in seen:
            continue
        seen.add(mod_name)
        if mod_name not in PUBLIC_MODULES:
            continue
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        if hasattr(mod, tail):
            obj = getattr(mod, tail)
            return mod_name, tail, obj

    raise LookupError(f"symbol '{dotted}' not found in any public Newton module")


def describe_symbol(dotted: str) -> dict:
    """Return a JSON-serializable description of one public symbol."""
    module, name, obj = resolve_symbol(dotted)
    info: dict = {
        "name": name,
        "module": module,
        "kind": _kind_of(obj),
        "doc": inspect.getdoc(obj) or "",
    }
    try:
        sig = inspect.signature(obj)
        info["signature"] = str(sig)
    except (TypeError, ValueError):
        info["signature"] = None
    return info
