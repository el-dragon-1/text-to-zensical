# Text to Zensical

Browser-based tool for writing markdown content and collecting images, then exporting everything as a tidy, shareable directory.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

## Getting Started

You will need two files in the same folder on your computer:

- `docker-compose.yml` — provided by your administrator
- `.env` — provided by your administrator (contains your secret key and port)

Open a terminal, navigate to that folder, and run:

```bash
docker compose up -d
```

Then open your browser and go to:

```
http://localhost:10253
```

That's it. The app is running.

## Stopping the App

```bash
docker compose down
```

## Updating to the Latest Version

```bash
docker compose pull
docker compose up -d
```

Your existing projects and saved content are not affected by updates.

## Using the App

### Projects

- The left sidebar lists all your saved projects.
- Click **New Project** to start a fresh one.
- Click any project name to switch to it.
- Use the rename and delete controls in the sidebar to manage projects.

### Writing

- Type or paste markdown directly into the editor.
- Use the right-side toolbar to insert **Headers** (H1–H6), **Bold**, and **Italic** formatting.
- Use **Insert Admonition** to add a styled callout block (note, warning, tip, etc.).
- Use the **Line Break** button under Insert Admonition to insert a horizontal rule followed by spacing.

### Images

- Click **Image Upload** on the right toolbar to open the image overlay.
- Drag and drop an image file or click to select one.
- Set an optional width and caption before inserting.
- The image is inserted at your cursor position as a markdown figure block.

### Saving

- Click **Save Progress** to save the current editor content to your active project without downloading anything.
- Your scroll position and cursor location are preserved after saving.

### Preview

- Click **Preview Page** to save and open a live rendered preview of your content in a new browser tab.
- The preview tab refreshes automatically every 3 seconds as you continue editing and saving.
- Scroll position in the preview is maintained across refreshes.

### Export

- Click **Generate + Download** to export your project as a ZIP file.
- The ZIP contains `content.md` and all associated images in a single timestamped folder.

## Output Format

Exported folders are structured like this:

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

## Data Persistence

Your projects are saved in the `exports` folder inside your deployment directory. This folder is retained across app updates and restarts as long as you run Docker Compose from the same directory.

## Windows 11 Troubleshooting (Docker Desktop)

If this works on macOS but fails on Windows 11, check these first:

1. Use a local folder, not OneDrive/network storage

- Run the app from a local path like `C:\Users\<you>\text-to-zensical`.
- Avoid OneDrive-synced folders because file locking and sync latency can break bind mounts.

2. Confirm the `exports` bind mount is writable

```bash
docker compose ps
docker compose logs --tail=200 text-to-zensical
```

If logs show `PermissionError` or write failures under `/data/exports`, move the deployment folder to a normal local directory and restart.

3. Validate `.env` formatting

- Save `.env` as UTF-8 (no BOM).
- Keep one `KEY=value` per line.
- Do not wrap values in quotes unless needed.
- Ensure `SECRET_KEY` is set to a non-empty value.

4. Rebuild and restart cleanly

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose logs -f text-to-zensical
```

5. Check port conflicts

If `10253` is already in use, set another port in `.env`:

```env
PORT=10254
```

Then open `http://localhost:10254`.

6. If export/download fails intermittently

Recent builds generate ZIP files in a temporary container path (instead of the bind mount) to avoid Windows host file-lock edge cases.
