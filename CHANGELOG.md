# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-12-02

### Added
- Initial release of lightweight-charts-pro-backend
- Framework-agnostic FastAPI backend for TradingView Lightweight Charts
- REST API for CRUD operations on chart data
- WebSocket server for real-time chart updates
- Data chunking for efficient handling of large datasets
- Lazy loading support for on-demand data loading
- Pydantic models for request/response validation
- CORS support with configurable origins

### Changed
- Package renamed from `lightweight-charts-backend` to `lightweight-charts-pro-backend`
- Updated dependency reference to `lightweight-charts-pro`
- Updated all internal imports to use new package names

### Technical Details
- Built with FastAPI 0.111.0+
- Uses uvicorn for ASGI server
- WebSocket support with websockets 12.0+
- Depends on lightweight-charts-pro for core functionality

[unreleased]: https://github.com/nandkapadia/lightweight-charts-pro-backend/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nandkapadia/lightweight-charts-pro-backend/releases/tag/v0.1.0
