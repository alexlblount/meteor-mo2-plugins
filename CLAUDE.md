# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repository is for developing Mod Organizer 2 (MO2) plugins in Python, primarily for modded Skyrim. Always reference the included API documentation to ensure high-quality, compatible code.

## Repository Structure

```
├── docs/MO2 Python Plugin API/    # Complete MO2 API documentation
│   ├── 01-core-overview.rst.txt         # API overview and structure
│   ├── 02-file-operations.rst.txt       # File handling & data structures
│   ├── 03-plugin-interfaces.rst.txt     # All IPlugin* interfaces  
│   ├── 04-organizer-management.rst.txt  # IOrganizer & core management
│   ├── 05-utility-classes.rst.txt       # Helper classes & functions
│   ├── mo2-python-api.rst.txt           # Complete API (large, use sections above)
│   ├── mo2-widgets-api.rst.txt          # UI/Widget APIs (PyQt6)
│   ├── plugin-types.rst.txt             # Plugin type definitions
│   ├── setup-tools.rst.txt              # Plugin setup and installation
│   └── writing-plugins.rst.txt          # Plugin development guide
├── examples/                            # Reference implementations
├── projects/                            # Active plugin projects
└── docs/                               # Additional documentation
```

## API Documentation

**ALWAYS reference these files when writing MO2 plugins:**

**Core API References (organized for easy consumption):**
- `docs/MO2 Python Plugin API/01-core-overview.rst.txt` - Start here: API structure and overview
- `docs/MO2 Python Plugin API/02-file-operations.rst.txt` - File handling, FileTreeEntry, IFileTree
- `docs/MO2 Python Plugin API/03-plugin-interfaces.rst.txt` - All IPlugin* classes for plugin development
- `docs/MO2 Python Plugin API/04-organizer-management.rst.txt` - IOrganizer, IModList, IModInterface
- `docs/MO2 Python Plugin API/05-utility-classes.rst.txt` - Helper classes, enums, and utility functions

**Complete References:**
- `docs/MO2 Python Plugin API/mo2-python-api.rst.txt` - Complete API (38K lines, prefer sections above)
- `docs/MO2 Python Plugin API/mo2-widgets-api.rst.txt` - UI components (PyQt6-based)
- `docs/MO2 Python Plugin API/plugin-types.rst.txt` - Plugin architecture patterns
- `docs/MO2 Python Plugin API/writing-plugins.rst.txt` - Development guidelines

## Key MO2 Development Patterns

### Core Imports

```python
import mobase
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
```

### Essential APIs

- `organizer.modList()` - Access mod list operations
- `organizer.getMod(name)` - Get mod interface
- `mod.version().displayString()` - Get mod version
- `mobase.widgets.TaskDialog` - Custom dialog creation

## Example Implementations

Located in `examples/`:

- **`changeloggen.py`** - Compares modlists to generate changelogs organized by separators
- **`LazyModlistRenamer.py` / `LazyModlistUnRenamer.py`** - Canonical mod naming for organization and import ordering
- **`[NoDelete] Indexer.py`** - Auto-indexes mods/separators with NoDelete tag, includes backup system

## Known Issues & Solutions

### Critical Race Conditions

- **Issue**: Rapid mod name changes break `modlist.txt` updates
- **Solution**: Add delays between mod operations (see `LazyModlistRenamer.py` implementation)

### Mod List Ordering

- **Issue**: `modlist.txt` stores mods in reverse order
- **Solution**: Reverse order when displaying to users (reference `changeloggen.py:` examples)

## Development Guidelines

1. **Always use delays** when performing bulk mod operations
2. **Reference API docs** before implementing any mobase functionality  
3. **Test with small mod lists** before deploying to large installations
4. **Include error handling** for file operations and mod access
5. **Follow PyQt6 patterns** for UI components

## Recent Releases

- 16-AUG-2025: Released `no_delete_tagger.py` to Nexus: [NoDelete Tagger and Indexer](https://www.nexusmods.com/skyrimspecialedition/mods/157026)
