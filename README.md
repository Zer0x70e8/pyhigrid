# AlbusWall - Hyprland Image Gallery

**Your wall of memories, frame by frame.**  
*A clean grid gallery for your ricing shots.*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stage](https://img.shields.io/badge/stage-alpha-orange.svg)]()

> ⚠️ **Early Development Notice**  
> This project is still in **active development** (current version: **0.0.3**).  
> The GUI now displays images in a grid and lets you switch between albums — but interaction is limited to viewing only (no selection yet). A fully functional CLI backend is implemented and shares the same database.  
> It is a personal, spare‑time project — my very first public Python application. Progress is steady but may be slow. Contributions, feedback, and patience are deeply appreciated.

**albusWall** is an image grid tool designed to showcase your **Hyprland ricing setups** with a clean, HIG‑inspired interface.

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
git clone https://github.com/Zer0x70e8/albusWall.git
cd albusWall
pip install Pillow PySide6 
```

### Launch the GUI

```bash
cd src
python -m albuswall
```

### Command Line Interface (CLI)

The CLI provides full access to your media library — import, organise, manage trash, and inspect metadata — all from the terminal.  
**It uses the same database as the GUI**, so you can mix workflows.

```bash
cd src
python -m albuswall_cli --db <path/to/your/database.db> <subcommand>
```

If no `--db` is given, it defaults to `test_media.db` in the current directory.  
Use `python -m albuswall_cli --help` to see all available commands and `python -m albuswall_cli <command> --help` for details of a sub‑command.

#### Basic CLI Workflow

1. **Initialise the database**  
   ```bash
   python -m albuswall_cli --db my_library.db init
   ```

2. **Import images**  
   ```bash
   python -m albuswall_cli --db my_library.db import /path/to/images --recursive
   ```

3. **List your built‑in views**  
   ```bash
   python -m albuswall_cli --db my_library.db view
   ```

4. **See assets inside a view**  
   ```bash
   python -m albuswall_cli --db my_library.db view --view-id <UUID> --list-assets
   ```

5. **Inspect full metadata of an asset (debug interface)**  
   ```bash
   python -m albuswall_cli --db my_library.db get <asset-uuid>
   ```
   > ⚠️ **Note:** `get` is a **debug‑only** command. It exposes internal data structures and **may be removed or changed** in future releases. Use it for development exploration only.

6. **Soft‑delete an asset (move to trash)**  
   ```bash
   python -m albuswall_cli --db my_library.db trash delete <asset-uuid>
   ```

7. **Create and manage albums**  
   ```bash
   python -m albuswall_cli --db my_library.db album create "My Album"
   ```

All commands support common options: `--db` to specify the database, and `--log-level trace` for detailed logging.

## 📁 Project Layout

```text
src/
├── albuswall/                # GUI application
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
├── albuswall_cli/            # CLI interface (shared backend)
│   ├── commands/            # Sub‑command handlers (init, import, view, …)
│   ├── services/            # Business logic services (e.g. import)
│   └── __main__.py
├── assets/                  # Sample assets & default database (git‑ignored in real use)
└── test/                    # Tests
```

## 🧩 Dependencies

- Python ≥ 3.10
- Qt for Python – PySide6
- Pillow ≥ 10.0
- (CLI) No extra dependencies beyond the standard library and the project’s own modules

## 🛠 Development Status & Roadmap

- [x] Custom window frame (titlebar + action buttons)
- [ ] Theming infrastructure (only default theme, no switching yet)
- [x] Backend logic & database layer (repositories, services)
- [x] CLI interface for all core operations (init, import, view, trash, albums, debug `get`)
- [x] Logging system (file config support, CLI arguments override e.g. log level)
- [ ] Image directory scanner & thumbnail generator (wired to GUI, caching works but no cleanup yet)
- [ ] Configuration system (lightweight, static config in use; dynamic capabilities exist but not yet utilized)
- [x] Grid layout rendering & basic image viewing (view‑only, no selection yet)
- [x] Album switching in the GUI
- [ ] Album editing features (PRD in progress, service layer to be aligned with UI)
- [ ] Gallery interaction (selection, zoom)
- [ ] Single image detail view (requires virtual scrolling extensions, evaluating approaches)
- [ ] Settings GUI (will drive further configuration expansion)
- [ ] Packaging & proper PyPI release

I work on PyHIGrid in my free time. This is my first open‑source project, so the pace is deliberate — every line is a learning step. If you’re curious, feel free to explore the code, open issues, or even send a PR.

## 👤 About the Author

Zer0x70e8 – a solo developer passionate about Linux ricing, desktops aesthetics, and learning Python GUI development.  
GitHub: [@Zer0x70e8](https://github.com/Zer0x70e8)

## 📄 License

MIT – see [LICENSE](LICENSE) for details.

---

*AlbusWall – Your wall of memories, frame by frame.*
