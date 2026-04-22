"""Root conftest.py — adds src/ to sys.path so tests can import openteam."""
import sys
from pathlib import Path

# Add src/ so that `import openteam` works without installing the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Add AgentFoundation and RichPythonUtils so that `import agent_foundation` works
_repo_root = Path(__file__).parent.parent
for _dep in ["AgentFoundation/src", "RichPythonUtils/src"]:
    _dep_path = str(_repo_root / _dep)
    if _dep_path not in sys.path:
        sys.path.insert(0, _dep_path)
