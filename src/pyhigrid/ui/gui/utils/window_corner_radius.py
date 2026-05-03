#!/usr/bin/env python3
"""
跨平台系统窗口圆角半径获取工具
支持 Windows (7+), macOS (10.9+), Linux (X11/Wayland)
"""

import os
import platform
import subprocess
import sys
from typing import Optional


def get_windows_corner_radius() -> Optional[float]:
    """
    获取 Windows 系统默认窗口圆角半径。
    策略：
    - Windows 11 build >= 22000 且 DWM 圆角功能启用时，通常为 8px。
    - 若系统关闭圆角或使用其它策略，则为 0。
    - 早期 Windows 没有原生圆角，返回 0。
    """
    # 判断 Windows 版本
    try:
        build = sys.getwindowsversion().build  # type: ignore[attr-defined]
    except AttributeError:
        return None

    # Windows 11 起开始引入原生窗口圆角 (build 22000)
    if build < 22000:
        return 0.0

    # 检查是否全局禁用了窗口圆角
    rounding_enabled = True  # 默认启用
    # noinspection PyBroadException
    try:
        # noinspection PyCompatibility
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\DWM",
        ) as key:
            # 该注册表值可能存在也可能不存在，不存在即按默认启用处理
            value, _ = winreg.QueryValueEx(key, "EnableWindowCornerRounding")
            rounding_enabled = bool(value)
    except FileNotFoundError:
        pass
    except Exception:
        pass

    if not rounding_enabled:
        return 0.0

    # Windows 11 默认圆角半径（大圆角）约为 8 像素
    # 注意：此处无法区分“大圆角”和“小圆角”设置，取最常规值。
    return 8.0


def get_macos_corner_radius() -> Optional[float]:
    """
    获取 macOS 系统默认窗口圆角半径。
    尝试读取用户自定义值，若失败则根据系统版本给出经验值。
    """
    # 尝试通过 defaults 读取可能的全局圆角设置 (macOS 11+ 可能支持)
    for domain in ["NSGlobalDomain", "Apple Global Domain"]:
        for key in ["NSWindowCornerRadius", "AppleWindowCornerRadius"]:
            # noinspection PyBroadException
            try:
                result = subprocess.run(
                    ["defaults", "read", domain, key],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    return float(result.stdout.strip())
            except Exception:
                continue

    # 若未显式设置，根据系统版本返回经验默认值
    # noinspection PyBroadException
    try:
        ver_output = subprocess.check_output(
            ["sw_vers", "-productVersion"], text=True, timeout=2
        ).strip()
        major = int(ver_output.split(".")[0])
        # macOS 11 Big Sur 开始采用了与 iPadOS 类似的圆角，半径约为 8
        # macOS 10.15 及之前大约为 6
        if major >= 11:
            return 8.0
        else:
            return 6.0
    except Exception:
        # 完全无法判断时返回常见值
        return 7.0


def get_linux_corner_radius() -> Optional[float]:
    """
    获取 Linux 桌面环境默认窗口圆角半径。
    目前主要通过各桌面环境特有配置尝试获取，若无法获取则返回 None。
    """
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
    session = (os.environ.get("DESKTOP_SESSION") or "").lower()

    # ---------- GNOME (Mutter) ----------
    if "gnome" in desktop or "gnome" in session:
        # GNOME 的圆角由主题控制，没有统一的 gsettings 键值。
        # 可以通过解析当前 GTK 主题的 CSS 来试探，但这不可靠。
        # 此处尝试检测常见扩展或设置。
        # 已知 GNOME 42+ 默认 Adwaita 主题圆角半径为 8px
        return 8.0

    # ---------- KDE Plasma ----------
    if "kde" in desktop or "plasma" in session:
        # KDE 窗口装饰的圆角半径可通过 kwinrc 读取
        # noinspection PyBroadException
        try:
            import configparser
            kwinrc_path = os.path.join(
                os.environ.get("XDG_CONFIG_HOME",
                               os.path.expanduser("~/.config")),
                "kwinrc"
            )
            config = configparser.ConfigParser()
            config.read(kwinrc_path)
            # [org.kde.kdecoration2] 下的 BorderSize 和 CornerRadius
            corner = config.get("org.kde.kdecoration2", "CornerRadius",
                                fallback=None)
            if corner is not None:
                return float(corner)
        except Exception:
            pass
        # 默认 Breeze 主题的圆角半径约为 3px
        return 3.0

    # ---------- 其他桌面环境 ----------
    # 可以继续针对 Xfce, Cinnamon 等添加类似启发式逻辑，此处省略
    return None


def get_system_window_corner_radius() -> Optional[float]:
    """
    对外统一接口，返回当前操作系统默认窗口圆角半径（像素）。
    若无法判断，返回 None。
    """
    system = platform.system()
    if system == "Windows":
        return get_windows_corner_radius()
    elif system == "Darwin":
        return get_macos_corner_radius()
    elif system == "Linux":
        return get_linux_corner_radius()
    else:
        return None


def main():
    radius = get_system_window_corner_radius()
    if radius is None:
        print("未检测到系统窗口圆角信息（未知桌面环境或系统）")
    else:
        print(f"系统默认窗口圆角半径: {radius:.1f} px")


if __name__ == "__main__":
    main()