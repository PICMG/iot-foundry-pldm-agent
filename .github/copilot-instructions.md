<!-- Copilot / AI agent guidance for iot-foundry-pldm-agent -->
# Copilot instructions — iot-foundry-pldm-agent

Purpose: give AI coding agents immediate, actionable context so they can make small, correct changes.

- **Repository layout:**
  - `src/` — primary implementation (start here to find protocol handlers).
  - `subprojects/` — related components or vendored projects; check for language-specific build files.
  - `assets/` — static assets (e.g. `assets/pldm-agent.svg`).
  - `README.md` — top-level overview; updated with the project SVG.

- **Where to begin:**
  - Open `README.md` for project intent and high-level context.
  - Search the repo for the token `pldm` to locate protocol handlers and integration points.

- **Build / test hints (discoverable):**
  - There is no single top-level build script in this repo. Inspect `subprojects/` for `Makefile`, `CMakeLists.txt`, `package.json`, `pyproject.toml`, or `setup.py` to learn per-subproject build/test commands.

- **Coding patterns & conventions (to follow):**
  - Prefer minimal, focused edits that match the file's existing style and structure.
  - If changing public behavior, update `README.md` or add docs under a relevant directory.

- **Integration points to check:**
  - Look for networking, IPC, or platform-specific initialization code inside `src/` and `subprojects/`.
  - Validate cross-component changes by searching for function names or constants across the tree.

- **Merging guidance:**
  - If this file already exists, merge any unique project-specific notes and preserve explicit directives below.

- **Agent-specific directive:**
  - Enable Claude Haiku 4.5 for all clients

If anything here is unclear or you'd like examples inserted (code snippets, exact file pointers), ask and I will update this file.