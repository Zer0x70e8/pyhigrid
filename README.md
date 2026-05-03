# PyHIGrid - Hyprland Image Gallery

**Say Hi to your memories, frame by frame.**
*A HIG‑like grid for the memories you hold.*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stage](https://img.shields.io/badge/stage-alpha-orange.svg)]()

> ⚠️ **Early Development Notice**  
> This project is still in **active development**. Currently, only the graphical user interface is implemented; the full image loading and gallery logic is yet to be wired up.  
> It is a personal, spare‑time project — my very first public Python application. Progress is steady but may be slow. Contributions, feedback, and patience are deeply appreciated.

**PyHIGrid** is an image grid tool designed to showcase your **Hyprland ricing setups** with a clean, HIG‑inspired interface. Once complete, it will turn a folder of screenshots or photos into a beautiful, scrollable gallery — perfect for sharing your desktop aesthetics.

## ✨ Planned Features (current focus)

- **HIG‑like grid layout** – Images displayed in a responsive, uniform grid.
- **Custom title bar & window controls** – Native‑looking minimize/maximize/close buttons integrated into the window.
- **Theming** – QSS stylesheet support; a default theme is included.
- **Smooth scrolling & marquee labels** – Fluid browsing with animated labels.
- **Windows 11 awareness** – Automatic corner radius adjustment for Windows 11.
- **Purpose‑built for ricing shots** – Tailored to present your Hyprland (or any WM) creations.

## 🚀 Quick Start (for developers & testers)

**There is no installation step yet.**  
Simply clone the repository and run the module directly:

```bash
git clone https://github.com/Zer0x70e8/pyhigrid.git
cd pyhigrid
```

Make sure you have Python 3.10+ and a Qt binding (e.g., PySide6 or PyQt6) installed, as well as Pillow:

```bash
pip install Pillow PySide6   # or PyQt6
```

Then launch the UI:

```bash
python -m pyhigrid
```

A proper pip install procedure will be added once the core functionality stabilises.

## 📁 Project Layout

```text
src/pyhigrid/
├── configue/                # Configuration system (in progress)
├── core/                    # Application lifecycle
├── resources/               # QSS themes, icons
├── ui/gui/
│   ├── core/                # Window, titlebar, content area (mostly UI)
│   ├── utils/               # Window utilities (resizer, corners, etc.)
│   └── widget/              # Reusable widgets (toolbar, album grid placeholder, action buttons)
└── __main__.py              # Entry point
```

## 🧩 Dependencies

- Python ≥ 3.10
- Qt for Python – PySide6, PySide2, PyQt6, or PyQt5 (choose one)
- Pillow ≥ 10.0
- (Optional CLI) click + rich (future)

## 🛠 Development Status & Roadmap

- [x] Custom window frame (titlebar + action buttons)
- [x] Theming infrastructure
- [ ] Image directory scanner & thumbnail generator
- [ ] Grid layout rendering
- [ ] Full gallery interaction (selection, zoom, metadata)
- [ ] Packaging & proper PyPI release

I work on PyHIGrid in my free time. This is my first open‑source project, so the pace is deliberate — every line is a learning step. If you’re curious, feel free to explore the code, open issues, or even send a PR.

## 👤 About the Author

Zer0x70e8 – a solo developer passionate about Linux ricing, desktops aesthetics, and learning Python GUI development.  
GitHub: @Zer0x70e8

## 📄 License

MIT – see LICENSE for details.

PyHIGrid – Say Hi to your memories, frame by frame.