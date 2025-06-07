# pyS4 Avatar Maker

A modern, dark-mode-only Python fork of the PS4-Xplorer Avatar Maker, built with PyQt.

## Features
- Select and preview a PNG/JPG avatar image
- Export avatar package in .xavatar (ZIP) format with all required DDS/PNG sizes
- Supports both Local and Offline Activated user types
- All image processing and packaging handled natively in Python
- Robust error handling and user feedback
- Modular, testable codebase

## Setup
1. Install [rye](https://github.com/astral-sh/rye) and run `rye sync` to set up dependencies.
2. Run the app: `python -m pys4_avatar_maker`

## Project Structure
- `src/` - Main application code (models, services, controllers, UI)
- `tests/` - Pytest-based tests
- `docs/` - Documentation
- `config/` - Configuration files

## License
MIT 