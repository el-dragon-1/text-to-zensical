# Text to Zensical

Browser-based tool for collecting text and dropped images, then creating a single export directory with markdown output.

## Features

- Paste or type freeform text directly into the text area. 
- Use the clean right-side toolbar with a Headers dropdown (H1-H6), plus Bold and Italic tools.
- Use the Line Break button under Insert Admonition to insert `---` followed by two returns at the cursor.
- Main editor and Preview page share a Zensical modern-style visual theme.
- Use "Preview Page" in the bottom action row to auto-save, then open a static markdown preview in a new tab.
- Preview reuses one browser tab for the active project.
- Saved project previews auto-refresh every 3 seconds with in-place updates and scroll anchoring so users stay near their current reading position.
- Save Progress preserves editor page and source text scroll position after the save redirect.
- Use the top-right "Documentation" button to open a rendered preview of this README in a new tab.
- Use the right-side "Image Upload" button to open an overlay prompt with drag/drop plus image width and caption inputs.
- Use the right-side "Insert Admonition" button to open an overlay with type selection and body text for markdown admonition blocks.
- Admonition blocks now render in Preview using markdown admonition extensions.
- Upload settings apply directly when inserting image markdown from dropped/selected files.
- Images are inserted into the text area at the current cursor position using markdown figure syntax.
- Inserted figure blocks are automatically spaced with clean blank lines around them.
- Switch between saved projects from the left-side project directory.
- Rename and delete projects from the left-side project directory.
- View project thumbnail previews from saved images in the project list.
- Save Progress stores work to the active project without downloading a ZIP.
- Save/Export actions are docked at the bottom-right for quick access while editing.
- Generate one timestamped directory that contains:
  - `content.md` with your exact text area content and image blocks where you placed them.
  - copied image files in the same project root as `content.md`.
- Download a ZIP of the generated directory immediately after export.
- Handles duplicate filenames by appending numeric suffixes.

## Requirements

- Docker + Docker Compose

## Share With Other Users

Use Docker image distribution as the default sharing model.

### Team Handoff Pack

- `TEAM_HANDOFF.md` contains publisher and team consumer copy/paste steps.
- `.env.team.example` is the recommended team runtime template for release deployments.

### 1) Production Compose File (Image-Based)

- `docker-compose.release.yml` runs from a published image tag (no local source build required).
- `.env.example` provides runtime variables and security defaults.

### 2) Environment Template And Security Defaults

- Copy `.env.example` to `.env`.
- Set a strong `SECRET_KEY` before sharing or deployment.
- The release compose file includes lightweight container hardening:
  - `no-new-privileges`
  - dropped Linux capabilities
  - `tmpfs` mount for `/tmp`

### 3) Release/Startup Instructions

#### Publisher workflow (build and publish image)

```bash
cd /Users/davidpolizzi/Development/docker/text-to-zensical

export IMAGE=ghcr.io/el-dragon-1/text-to-zensical
export TAG=v1.0.0

docker build -t "${IMAGE}:${TAG}" -t "${IMAGE}:latest" .
docker push "${IMAGE}:${TAG}"
docker push "${IMAGE}:latest"
```

#### User workflow (run published release)

```bash
cd /Users/davidpolizzi/Development/docker/text-to-zensical
cp .env.example .env

# Edit .env with your published image and a strong SECRET_KEY.
docker compose -f docker-compose.release.yml up -d
```

Then open:

```bash
http://localhost:10253
```

Use a different host port if needed:

```bash
PORT=8000 docker compose -f docker-compose.release.yml up -d
# then open http://localhost:8000
```

Stop:

```bash
docker compose -f docker-compose.release.yml down
```

## Run With Docker

```bash
cd /Users/davidpolizzi/Development/docker/text-to-zensical
docker compose up --build
```

If the workflow fails with `permission_denied: write_package`, open the GHCR package settings for `text-to-zensical` and grant this repository write access under Actions access.

Use a different host port if needed:

```bash
PORT=8000 docker compose up --build
# then open http://localhost:8000
```

Then open:

```bash
http://localhost:10253
```

Generated project folders are persisted on your host at `./exports`, and the left sidebar lets you switch between them.

## Stop

```bash
docker compose down
```

## Local Python Run (Optional)

```bash
cd /Users/davidpolizzi/Development/docker/text-to-zensical
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Output Format

The app creates a folder named like `zensical-export-YYYYMMDD-HHMMSS` under the output root (`/data/exports` in the container, mapped to `./exports` on host).

Example structure:

```text
zensical-export-20260603-121314/
  content.md
  photo-1.png
  screenshot.jpg
```

Example markdown output:

```markdown
Your entered text goes here.

<figure markdown="span">
  ![photo-1.png](photo-1.png){ width="300" }
  <figcaption>Custom caption text</figcaption>
</figure>
```
