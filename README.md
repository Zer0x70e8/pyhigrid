# PyHIGrid - Hyprland Image Gallery

**Say Hi to your memories, frame by frame.**  
*A HIG‑like grid for the memories you hold.*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stage](https://img.shields.io/badge/stage-alpha-orange.svg)]()

> ⚠️ **Early Development Notice**  
> This project is still in **active development**. Currently, the graphical user interface and a fully functional CLI backend are implemented; the image loading pipeline is being wired into the GUI.  
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

**There is no pip installation yet.**  
Clone the repository and install the required dependencies:

```bash
git clone https://github.com/Zer0x70e8/pyhigrid.git
cd pyhigrid
pip install Pillow PySide6 
```

### Launch the GUI

```bash
cd src
python -m pyhigrid
```

### Command Line Interface (CLI)

The CLI provides full access to your media library — import, organise, manage trash, and inspect metadata — all from the terminal.  
**It uses the same database as the GUI**, so you can mix workflows.

```bash
cd src
python -m pyhigrid_cli --db <path/to/your/database.db> <subcommand>
```

If no `--db` is given, it defaults to `test_media.db` in the current directory.  
Use `python -m pyhigrid_cli --help` to see all available commands and `python -m pyhigrid_cli <command> --help` for details of a sub‑command.

#### Basic CLI Workflow

1. **Initialise the database**  
   ```bash
   python -m pyhigrid_cli --db my_library.db init
   ```

2. **Import images**  
   ```bash
   python -m pyhigrid_cli --db my_library.db import /path/to/images --recursive
   ```

3. **List your built‑in views**  
   ```bash
   python -m pyhigrid_cli --db my_library.db view
   ```

4. **See assets inside a view**  
   ```bash
   python -m pyhigrid_cli --db my_library.db view --view-id <UUID> --list-assets
   ```

5. **Inspect full metadata of an asset (debug interface)**  
   ```bash
   python -m pyhigrid_cli --db my_library.db get <asset-uuid>
   ```
   > ⚠️ **Note:** `get` is a **debug‑only** command. It exposes internal data structures and **may be removed or changed** in future releases. Use it for development exploration only.

6. **Soft‑delete an asset (move to trash)**  
   ```bash
   python -m pyhigrid_cli --db my_library.db trash delete <asset-uuid>
   ```

7. **Create and manage albums**  
   ```bash
   python -m pyhigrid_cli --db my_library.db album create "My Album"
   ```

All commands support common options: `--db` to specify the database, and `--verbose` for detailed logging.

## 📁 Project Layout

```text
src/
├── pyhigrid/                # GUI application
│   ├── configue/            # Configuration system
│   ├── core/                # Application lifecycle
│   ├── domain/              # Domain models & constants
│   ├── infrastructure/      # Database bootstrapping & connection
│   ├── repository/          # Data access layer
│   ├── resources/           # QSS themes, icons, SQL schemas
│   ├── ui/                  # GUI components
│   │   └── gui/
│   │       ├── widget/      # Reusable widgets
│   │       ├── window/      # Frameless window & title bar
│   │       └── ...
│   └── __main__.py
├── pyhigrid_cli/            # CLI interface (shared backend)
│   ├── commands/            # Sub‑command handlers (init, import, view, …)
│   ├── services/            # Business logic services (e.g. import)
│   └── __main__.py
├── assets/                  # Sample assets & default database (git‑ignored in real use)
└── test/                    # Tests
```

## 🧩 Dependencies

- Python ≥ 3.10
- Qt for Python – PySide6, PySide2, PyQt6, or PyQt5 (choose one)
- Pillow ≥ 10.0
- (CLI) No extra dependencies beyond the standard library and the project’s own modules

## 🛠 Development Status & Roadmap

- [x] Custom window frame (titlebar + action buttons)
- [x] Theming infrastructure
- [x] Backend logic & database layer (repositories, services)
- [x] CLI interface for all core operations (init, import, view, trash, albums)
- [x] Debug inspection command (`get`) – may be temporary
- [ ] Image directory scanner & thumbnail generator (wiring to GUI)
- [ ] Grid layout rendering
- [ ] Full gallery interaction (selection, zoom, metadata)
- [ ] Packaging & proper PyPI release

I work on PyHIGrid in my free time. This is my first open‑source project, so the pace is deliberate — every line is a learning step. If you’re curious, feel free to explore the code, open issues, or even send a PR.

## 👤 About the Author

Zer0x70e8 – a solo developer passionate about Linux ricing, desktops aesthetics, and learning Python GUI development.  
GitHub: [@Zer0x70e8](https://github.com/Zer0x70e8)

## 📄 License

MIT – see [LICENSE](LICENSE) for details.

---

*PyHIGrid – Say Hi to your memories, frame by frame.*
