#
""""""

import sys
import logging
import ctypes
from ctypes import wintypes

import pyhigrid

# noinspection SpellCheckingInspection
DWMWA_WINDOW_CORNER_PREFERENCE = 33
# noinspection SpellCheckingInspection
DWMWCP_DONOTROUND = 1

logger = logging.getLogger(
    f"{pyhigrid.__name__}.__ui__.utils.disable_win11_round_corners"
)

def disable_round_corners(hwnd: int, auto_platform: bool=True) -> bool:
    """尝试禁用 Windows 11 的窗口圆角，返回是否成功"""
    if auto_platform and sys.platform != 'win32':
        return False
    try:
        # noinspection SpellCheckingInspection
        dwmapi = ctypes.cdll.LoadLibrary("dwmapi.dll")
        func = getattr(dwmapi, "DwmSetWindowAttribute", None)
        if func is None:
            return False
        func(
            wintypes.HWND(hwnd),
            wintypes.DWORD(DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(wintypes.DWORD(DWMWCP_DONOTROUND)),
            ctypes.sizeof(wintypes.DWORD),
        )
        return True
    except Exception as e:
        logger.error(e)
        return False
