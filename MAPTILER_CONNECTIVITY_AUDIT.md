# SIH26069 — Map Connectivity Audit & Fix Report

**Date:** September 11, 2026  
**Auditor:** Automated Diagnostic Agent  
**Project Root:** `D:\SIH\SIH26069`  
**Scope:** Frontend map tile rendering, `VITE_MAPTILER_API_KEY` environment propagation

---

## Root Cause

Two independent root causes were identified through direct source-code inspection and live browser verification:

### Root Cause 1 — Vite `envDir` mismatch (FIXED)

| Item | Value |
|---|---|
| Root `.env` path | `D:\SIH\SIH26069\.env` |
| Vite project root | `D:\SIH\SIH26069\services\frontend\` |
| Vite default `envDir` | Same as project root → `services/frontend/` |
| `.env` in `services/frontend/`? | **ABSENT** |
| Effect | `import.meta.env.VITE_API_URL` and `import.meta.env.VITE_MAPTILER_API_KEY` resolved to `undefined` at runtime |

**Fix:** Added `envDir: repoRoot` to `vite.config.js` pointing two levels up to the project root.

### Root Cause 2 — Tile provider is CartoCDN, not MapTiler (NO CODE CHANGE REQUIRED)

Every map component in the codebase uses **CartoCDN raster tiles** via react-leaflet, not MapTiler SDK tiles.  
CartoCDN's free/unauthenticated raster basemap endpoint embeds a **diagonal "API KEY REQUIRED" watermark** baked into the PNG tile images themselves when no registered CARTO API key is presented.

This is a **CARTO policy watermark** — it is not:
- A JavaScript error
- A Leaflet overlay
- A MapTiler error
- Our own frontend code
- A network failure

The tiles return HTTP 200 but the image pixels contain the watermark.

---

## Environment Verification

| Check | Result |
|---|---|
| Root `.env` detected at `D:\SIH\SIH26069\.env` | PASS |
| `VITE_API_URL` present in root `.env` | PASS |
| `VITE_MAPTILER_API_KEY` present in root `.env` | PASS |
| Vite `envDir` configured to project root | PASS (after fix) |
| `services/frontend/.env` created (duplication) | NOT CREATED (correct — avoided) |
| Actual key value exposed in any log/report/screenshot | NO |

---

## Map Provider Verification

Source inspection (all four map components, exact tile URLs):

| Component | File | Tile Provider | API Key Used? |
|---|---|---|---|
| `IndiaEventMap` | `components/command-center/IndiaEventMap.jsx` | **CartoCDN** | No |
| `GeospatialIntelligence` | `pages/GeospatialIntelligence.jsx` | **CartoCDN** | No |
| `EmergingEvents` | `pages/EmergingEvents.jsx` | **CartoCDN** | No |
| `EventIntelligence` | `pages/EventIntelligence.jsx` | **CartoCDN** | No |

URL pattern used by all: `https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png`

`VITE_MAPTILER_API_KEY` is **not read** by any source file — no `import.meta.env.VITE_MAPTILER_API_KEY` reference exists in frontend code. The key is correctly loaded by Vite after the `envDir` fix, but is currently unused.

---

## Leaflet CSS

| Check | Result |
|---|---|
| `import 'leaflet/dist/leaflet.css'` in `IndiaEventMap.jsx` | PASS — Line 11 |
| `import 'leaflet/dist/leaflet.css'` in `GeospatialIntelligence.jsx` | PASS — Line 5 |
| `import 'leaflet/dist/leaflet.css'` in `EventIntelligence.jsx` | PASS — Line 5 |
| `EmergingEvents.jsx` | Inherited via component tree |
| `leaflet/dist/leaflet.css` present in `node_modules` | PASS |

---

## Browser Test Results (Live)

Vite dev server started at `http://localhost:5173/` — clean startup, zero errors.

| Test | Result |
|---|---|
| Page loads | YES |
| Map renders | YES — India map with state boundaries and city markers |
| Tile requests HTTP status | 200 OK from `cartocdn.com` |
| Console JavaScript errors | ZERO |
| Console warnings | React Router v7 future flags (pre-existing, unrelated) |
| **"API KEY REQUIRED" visible** | YES — diagonal watermark baked into tile pixels by CartoCDN |
| Watermark source | **CartoCDN** — embedded in tile image PNGs |
| Event markers visible | YES |
| City beacons (Mumbai, Nagpur, Nashik) | YES |
| Zoom in/out | FUNCTIONAL |
| Pan/drag | FUNCTIONAL |
| Geospatial Intelligence page | RENDERS (same watermark) |
| Emerging Events page | RENDERS (same watermark) |
| SSE / live event feed | UNTOUCHED — not modified |

---

## Error Source — Definitive Answer

> **"API KEY REQUIRED"**

| Attribution | Verdict |
|---|---|
| MapTiler | NOT MapTiler — MapTiler is not installed, not called, not referenced |
| Leaflet JavaScript | NOT Leaflet — zero console errors |
| Our frontend code | NOT our code — no such string anywhere in source |
| Browser / CORS / network failure | NOT a network failure — tiles return HTTP 200 |
| **CartoCDN raster tile images** | **THIS IS THE SOURCE** |

CARTO embeds the watermark text directly into tile PNG pixels when requests arrive without a valid CARTO API key or from a domain not registered in CARTO's dashboard. This is a **CARTO billing/usage policy**, not a code bug.

---

## Files Changed

| File | Change |
|---|---|
| `services/frontend/vite.config.js` | Added `envDir: repoRoot` (resolves 2 levels up to project root) |
| `docker-compose.yml` | Added `VITE_MAPTILER_API_KEY: ${VITE_MAPTILER_API_KEY}` to frontend environment block |

No other files were modified.

---

## Docker / Production Build Path

The frontend `Dockerfile` runs `npm run dev` — **it does not perform a production Vite build**.  
`VITE_*` variables are injected at dev-server start time via the container environment.

```
D:\SIH\SIH26069\.env
       ↓ (Docker Compose ${} substitution)
docker-compose.yml environment block
       ↓
Container environment variable
       ↓
Vite dev server reads via envDir
       ↓
import.meta.env.VITE_MAPTILER_API_KEY available in browser JS
```

---

## Remaining Issue: CARTO Watermark

The "API KEY REQUIRED" watermark requires one of the following (design decision required):

| Option | Action | Notes |
|---|---|---|
| **A. Register CARTO API key** | Account at carto.com, add `CARTO_API_KEY` to `.env`, update tile URLs | Free tier available |
| **B. Switch to OpenStreetMap** | Change `url=` in all 4 TileLayers to `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` | Free, no key, no watermark |
| **C. Use MapTiler (key already in `.env`)** | Change tile URLs to MapTiler vector/raster style endpoint with `?key=` | Key already configured and now loaded |

---

## Security

| Check | Result |
|---|---|
| Actual API key exposed in any file/log/screenshot | NO |
| `VITE_MAPTILER_API_KEY` hardcoded | NO |
| Unrelated secrets exposed | NO |

---

## Summary

```
ROOT CAUSE:      (1) Vite envDir not set → VITE_* vars undefined (FIXED)
                 (2) CartoCDN tile policy → "API KEY REQUIRED" watermark
                     baked into tile PNG pixels (NOT a code bug)

FIX APPLIED:     services/frontend/vite.config.js — envDir → project root
                 docker-compose.yml — VITE_MAPTILER_API_KEY forwarded to container

MAP PROVIDER:    CartoCDN (basemaps.cartocdn.com) — all 4 components
                 MapTiler is NOT used anywhere in source code

MAP STATUS:      RENDERS — tiles load HTTP 200, markers visible, zoom/pan work
                 CARTO "API KEY REQUIRED" watermark still present (see options above)

ENV STATUS:      VITE_API_URL          : PRESENT
                 VITE_MAPTILER_API_KEY : PRESENT (loaded, currently unused by map code)

FILES CHANGED:   services/frontend/vite.config.js
                 docker-compose.yml
```
