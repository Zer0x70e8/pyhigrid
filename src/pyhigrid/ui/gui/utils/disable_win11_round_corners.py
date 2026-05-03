#
""""""

import ctypes
from ctypes import wintypes

# noinspection SpellCheckingInspection
DWMWA_WINDOW_CORNER_PREFERENCE = 33
# noinspection SpellCheckingInspection
DWMWCP_DONOTROUND = 1

def disable_round_corners(hwnd: int) -> bool:
    """尝试禁用 Windows 11 的窗口圆角，返回是否成功"""
    # noinspection PyBroadException
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
        print(e)
        return False
