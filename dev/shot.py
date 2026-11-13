"""Frames of the scene from any copy of the tools, for review. Used by the other scripts of this folder.

    frame(tools, when, weather, state, tick=20, skip=('dog', 'dog_shadow', 'text'))  ->  PIL RGB image, 480 x 270
"""
import importlib
import sys
from pathlib import Path

from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ADDON_TOOLS = ROOT / 'tools'
OUT = ROOT / 'out'                 # review pictures: untracked
OUT.mkdir(parents=True, exist_ok=True)
_loaded = {}


def scene_of(tools):
    """The scene module of one copy of the tools (each copy reads its own art/)."""
    tools = str(Path(tools).resolve())
    if tools not in _loaded:
        for name in [n for n in sys.modules if n == 'scene' or n.startswith('scene_')]:
            del sys.modules[name]
        sys.path.insert(0, tools)
        _loaded[tools] = importlib.import_module('scene')
        sys.path.remove(tools)
        del sys.modules['scene']
    return _loaded[tools]


def frame(tools, when, weather, state, tick=20, skip=('dog', 'dog_shadow', 'text')):
    sc = scene_of(tools)
    idx, rgb, _ = sc.indexes(when, weather, tick, state, skip)
    return Image.fromarray(rgb[idx])
