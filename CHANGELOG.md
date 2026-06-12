# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-06-12

### Added
- Initial release 🎉
- CustomTkinter GUI with Light/Dark/System themes
- Multi-file upload via file dialog and drag & drop (folders scanned recursively)
- Per-file **Convert** button and batch **Convert all**
- Background-threaded conversion (2 in parallel), live status, progress bar
- Optional output folder (default: next to each source file)
- "Open .md" shortcut after a successful conversion
- About dialog (author, version, repo link) with **Check for updates** against GitHub Releases
- Light theme by default, with Dark and System modes
- Windows installer (Inno Setup) and Linux packages (.deb + tarball)
- GitHub Actions: CI (lint + tests) and release builds for Windows/Linux
