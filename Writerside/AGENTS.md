# Repository Guidelines

## Project Structure & Module Organization
This repository is a JetBrains Writerside documentation project. Keep authored content in `topics/`, shared images in `images/`, and Writerside metadata in the root:

- `writerside.cfg` wires the project together.
- `PQCCN.tree` defines the published table of contents and start page.
- `c.list` and `v.list` store categories and shared variables.

Add new articles under `topics/` and register them in `PQCCN.tree`. Match the existing naming pattern: Title-Case filenames with hyphens, for example `Quick-Setup-Guide.md`.

## Build, Test, and Development Commands
There is no repo-local build script committed here. Use Writerside tooling to preview and validate the docs:

- Open the project in JetBrains Writerside and preview `PQCCN.tree` to verify navigation and rendering.
- Build the Writerside instance configured by `writerside.cfg` before opening a PR.
- Run `git diff --check` to catch trailing whitespace and malformed patch formatting.

When editing setup instructions, validate referenced commands against the companion environment. Current examples in the docs include `docker build .`, `docker compose up`, and `pip install numpy docker_on_whales pyyaml tqdm`.

## Coding Style & Naming Conventions
Use short Markdown sections with ATX headings (`#`, `##`) and concise paragraphs. Keep filenames descriptive and stable; rename topics only when the TOC is updated in the same change. Preserve relative links such as `[Data-Collection](Data-Collection.md)`.

For XML files (`writerside.cfg`, `PQCCN.tree`, `c.list`, `v.list`), keep the existing 4-space indentation and do not reorder entries without a reason.

## Testing Guidelines
This repo does not contain an automated test suite. Treat documentation validation as the test:

- confirm each changed page renders in Writerside preview;
- verify links, image paths, and TOC entries;
- re-check command samples for accuracy and copy/paste safety.

## Commit & Pull Request Guidelines
Recent commits use short, imperative summaries, mostly in English, with occasional Chinese. Follow that style: one-line subject, action first, for example `Update setup guide for Docker prerequisites`.

PRs should include a brief description of the documentation change, note any affected topic files, link the related issue or task, and attach screenshots only when the rendered output or diagrams changed.
