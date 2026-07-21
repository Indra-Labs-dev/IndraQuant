"""Plugin System (Phase 6, docs/05): third-party extensions live in
`backend/plugins/<name>/plugin.py` and expose `PLUGIN = PluginDescriptor(...)`.
Each plugin router is mounted under `/api/v1/plugins/<name>` at startup —
the core never imports a plugin directly, so removing a plugin folder is
enough to remove the feature.
"""

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter

PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"


@dataclass(frozen=True)
class PluginDescriptor:
    name: str
    version: str
    router: APIRouter


def discover_plugins() -> list[PluginDescriptor]:
    if not PLUGINS_DIR.is_dir():
        return []

    plugins: list[PluginDescriptor] = []
    for entry in sorted(PLUGINS_DIR.iterdir()):
        plugin_file = entry / "plugin.py"
        if not entry.is_dir() or not plugin_file.is_file():
            continue

        spec = importlib.util.spec_from_file_location(
            f"indraquant_plugin_{entry.name}", plugin_file
        )
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        descriptor = getattr(module, "PLUGIN", None)
        if isinstance(descriptor, PluginDescriptor):
            plugins.append(descriptor)
    return plugins
