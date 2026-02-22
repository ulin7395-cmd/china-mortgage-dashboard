import sys
import pytest
from pathlib import Path

# 确保项目根目录在 sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
