#!/usr/bin/env python3
"""使 CLI 可通过 python -m pyhigrid_cli 启动"""
import sys
from pathlib import Path

# 添加项目 src 路径，保证导入 pyhigrid
src_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_path))

from pyhigrid_cli.main import main

if __name__ == "__main__":
    main()
