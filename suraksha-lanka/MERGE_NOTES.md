# Merge summary

This folder combines the source changes from both supplied ZIP files.

- Preserved the manual flood/landslide input screen and its map/API integration.
- Preserved the risk-aware route optimization screen and route API service.
- Added both features to the main navigation and home screen.
- Kept generated folders (`node_modules` and `.expo`) out of the Git-ready archive.
- Removed the hard-coded Google Maps key from `app.json`; configure it through `.env` using `.env.example`.
- Verified with `npm install` and `npm run typecheck`.

Before running, copy `.env.example` to `.env` and replace the placeholder values.
