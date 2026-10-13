# UnderBot website

A React + Vite project site for UnderBot: a general-purpose robot body for experiments with VLA and WAM models.

## Run locally

Requires Node.js 24 and npm.

```sh
npm ci
npm run dev
```

## Build and verify

```sh
npm run build
npm run test:e2e
```

The browser checks use an installed Chrome by default. Set `PLAYWRIGHT_CHANNEL=msedge` to use Edge, or adjust `playwright.config.js` for your environment. Tests launch the production preview automatically and cover the real model, viewpoint/wireframe controls, downloads, subsystem tabs, keyboard interactions, mobile navigation, responsive widths, accessible contrast, fallback behavior, joint controls and mimic motion. Screenshots are written to ignored `test-results/`.

## Pages

- `/`: project introduction, interactive R08 model, hardware, development status and resources.
- `/explorer`: the upstream offline URDF inspector, including joint sliders and collision geometry.
- `/dashboard`: compatibility route to the model explorer; the old mock telemetry is removed.

`vercel.json` retains Vite hosting and handles direct requests to both app routes. Deploy previews to the existing `underbot-website` Vercel project. A production release should use the same reviewed source revision.

## Content and provenance

- Navigation video: owner-provided Foxglove screen recording, 13 October 2026 (69 seconds). Shows the R08 model and A* navigation simulation in a point-cloud map. The web copy preserves the full recording at 2560 pixels wide, H.264 CRF 24 with fast-start metadata; its entirely silent audio track is omitted. The poster is taken at 60 seconds. Playback is user-initiated, with a visual description and download link at `/#demo`.
- Project purpose: owner-provided brief, 13 October 2026 — a general-purpose robot body for testing VLA and WAM models, aimed at project followers and collaborators.
- Hardware source: `gautamsajeen/UnderBot-Personal`, revision R08, commit `3f28a652bb34109b23241bd98b33f2c56ea0a87a`.
- Technical claims are based on the source README, URDF and `underbot_description/docs/accuracy_and_physics.md`.
- Model validation results are attributed to the source package; no physical payload, autonomy, current hardware capability or native ROS/simulator verification is claimed.
- Exact compute/LiDAR selections and the bare Kinect layout remain provisional. No team biographies, budgets, telemetry, contact addresses or performance numbers are invented.

The hero reconstructs the URDF link hierarchy from the upstream viewer's data, renders the actual STL meshes using Three.js, and uses URDF RPY rotations in ZYX order. Rendering happens on interaction and resize rather than in a continuous animation loop. The heavy renderer is loaded separately from the page. A source render and download link remain available if WebGL or model loading fails.

`public/model/viewer.html` and the downloadable archive are copied unmodified. `public/model/source.json` records their origin. To refresh from a reviewed robot checkout:

```sh
npm run sync:model -- ../UnderBot-Personal
```

After a model update, review the accompanying copy, source links and specifications in `src/App.jsx`; rerun the build and browser checks. The upstream design currently has no specified license; this website does not assign one.

## Before expanding the project story

Confirm physical build progress, measured hardware capabilities, selected VLA/WAM integrations, team credits and any real build photography with the project owners. Keep design intent distinct from measured results.
