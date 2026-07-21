"""Example plugin proving the Plugin System extension point (Phase 6).

Drop a new folder next to this one with its own `plugin.py` exposing a
module-level `PLUGIN = PluginDescriptor(name=..., version=..., router=...)`
to add endpoints without touching any core module. The router can reuse
public providers from `src.composition_root` (e.g. authentication) exactly
like a core module would.
"""

from fastapi import APIRouter, Depends

from src.composition_root import get_current_user
from src.modules.auth.application.dto import UserProfile
from src.shared.plugins.loader import PluginDescriptor

router = APIRouter()


@router.get("/ping")
def ping(user: UserProfile = Depends(get_current_user)) -> dict:
    return {"plugin": "example_ping", "status": "ok", "user": user.email}


PLUGIN = PluginDescriptor(name="example_ping", version="0.1.0", router=router)
