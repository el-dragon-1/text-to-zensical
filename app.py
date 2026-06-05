from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    abort,
    after_this_request,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from markdown import markdown
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}

OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "/data/exports")).resolve()
README_PATH = (Path(__file__).resolve().parent / "README.md").resolve()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")


def _dedupe_name(original_name: str, used_names: set[str]) -> str:
    candidate = original_name
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix

    index = 1
    while candidate.lower() in used_names:
        candidate = f"{stem}-{index}{suffix}"
        index += 1

    used_names.add(candidate.lower())
    return candidate


def _normalize_project_name(project_name: str | None) -> str | None:
    if not project_name:
        return None

    safe_name = secure_filename(project_name).strip("._-")
    return safe_name or None


def _project_dir(project_name: str | None) -> Path | None:
    safe_name = _normalize_project_name(project_name)
    if not safe_name:
        return None

    project_dir = OUTPUT_ROOT / safe_name
    if not project_dir.exists() or not project_dir.is_dir():
        return None

    return project_dir


def _create_project(project_name: str | None = None) -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    safe_name = _normalize_project_name(project_name)
    if safe_name:
        project_dir = OUTPUT_ROOT / safe_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = f"zensical-project-{timestamp}"
        project_dir = OUTPUT_ROOT / base_name
        index = 1
        while project_dir.exists():
            project_dir = OUTPUT_ROOT / f"{base_name}-{index}"
            index += 1

    project_dir.mkdir(parents=True, exist_ok=True)
    content_path = project_dir / "content.md"
    if not content_path.exists():
        content_path.write_text("", encoding="utf-8")

    return project_dir


def _project_preview(project_dir: Path) -> str:
    content_path = project_dir / "content.md"
    if not content_path.exists():
        return "No content yet"

    try:
        lines = [line.strip() for line in content_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return "No content yet"

    if not lines:
        return "No content yet"

    return lines[0][:64]


def _project_image_paths(project_dir: Path) -> list[Path]:
    images: list[Path] = []

    for path in project_dir.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(path)

    legacy_images_dir = project_dir / "images"
    if legacy_images_dir.exists() and legacy_images_dir.is_dir():
        for path in legacy_images_dir.iterdir():
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(path)

    return images


def _thumbnail_name(project_dir: Path) -> str | None:
    images = _project_image_paths(project_dir)
    if not images:
        return None

    latest = max(images, key=lambda path: path.stat().st_mtime)
    return str(latest.relative_to(project_dir))


def _list_projects() -> list[dict[str, str]]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    projects: list[dict[str, str]] = []
    for project_dir in sorted(
        [path for path in OUTPUT_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        thumbnail_name = _thumbnail_name(project_dir)
        preview = _project_preview(project_dir)
        image_count = len(_project_image_paths(project_dir))

        project_data: dict[str, str] = {
            "name": project_dir.name,
            "preview": preview,
            "modified": datetime.fromtimestamp(project_dir.stat().st_mtime).strftime("%b %d, %Y %I:%M %p"),
            "image_count": str(image_count),
        }

        if thumbnail_name:
            project_data["thumbnail_url"] = url_for(
                "project_media",
                project_name=project_dir.name,
                image_path=thumbnail_name,
            )

        projects.append(project_data)

    return projects


def _load_project_content(project_dir: Path) -> str:
    content_path = project_dir / "content.md"
    if not content_path.exists():
        return ""

    return content_path.read_text(encoding="utf-8")


def _create_export(project_dir: Path, raw_text: str, uploaded_images: list) -> tuple[Path, int]:
    existing_names = {
        path.name.lower()
        for path in project_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    }
    copied_count = 0
    used_names: set[str] = set(existing_names)
    if uploaded_images:
        for uploaded in uploaded_images:
            original_name = secure_filename(uploaded.filename or "")
            if not original_name:
                continue

            suffix = Path(original_name).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
                continue

            target_name = _dedupe_name(original_name, used_names)
            target_path = project_dir / target_name
            uploaded.save(target_path)
            copied_count += 1

    markdown_path = project_dir / "content.md"
    markdown_path.write_text(raw_text, encoding="utf-8")

    return project_dir, copied_count


def _zip_export(export_dir: Path) -> Path:
    # Use a unique temp zip outside the bind mount to avoid host file-lock issues.
    tmp_dir = Path(tempfile.gettempdir()) / "text-to-zensical"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_dir / f"{export_dir.name}-{uuid.uuid4().hex}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for child in export_dir.rglob("*"):
            archive.write(child, child.relative_to(export_dir))
    return zip_path


def _rewrite_markdown_image_paths(raw_text: str, project_name: str | None) -> str:
    if not project_name:
        return raw_text

    def replacement(match: re.Match[str]) -> str:
        image_path = match.group(1).strip()
        if not image_path:
            return match.group(0)
        if "://" in image_path or image_path.startswith("data:") or image_path.startswith("#"):
            return match.group(0)

        path_without_query = image_path.split("?", 1)[0].split("#", 1)[0]
        if not path_without_query.lower().endswith(tuple(IMAGE_EXTENSIONS)):
            return match.group(0)

        image_url = url_for("project_media", project_name=project_name, image_path=image_path)
        return f"({image_url})"

    return re.sub(r"\(([^\)]+)\)", replacement, raw_text)


def _render_markdown_html(raw_text: str, project_name: str | None) -> str:
    text_for_render = _rewrite_markdown_image_paths(raw_text, project_name)
    return markdown(
        text_for_render,
        extensions=[
            "extra",
            "attr_list",
            "admonition",
            "pymdownx.details",
            "pymdownx.superfences",
        ],
    )


@app.get("/")
def index():
    projects = _list_projects()
    if not projects:
        active_project = _create_project()
        projects = _list_projects()
    else:
        requested_project = _project_dir(request.args.get("project"))
        active_project = requested_project or (OUTPUT_ROOT / projects[0]["name"])

    if active_project.name not in {project["name"] for project in projects}:
        active_project = OUTPUT_ROOT / projects[0]["name"]

    return render_template(
        "index.html",
        output_root=OUTPUT_ROOT,
        projects=projects,
        active_project=active_project.name,
        source_text=_load_project_content(active_project),
    )


@app.get("/projects/<project_name>/media/<path:image_path>")
def project_media(project_name: str, image_path: str):
    project_dir = _project_dir(project_name)
    safe_image = secure_filename(Path(image_path).name)

    if project_dir is None or not safe_image:
        abort(404)

    if Path(safe_image).suffix.lower() not in IMAGE_EXTENSIONS:
        abort(404)

    direct_path = project_dir / safe_image
    if direct_path.exists() and direct_path.is_file():
        return send_from_directory(project_dir, safe_image)

    legacy_images_dir = project_dir / "images"
    legacy_path = legacy_images_dir / safe_image
    if legacy_path.exists() and legacy_path.is_file():
        return send_from_directory(legacy_images_dir, safe_image)

    abort(404)


@app.post("/projects/new")
def create_project():
    project_dir = _create_project()
    flash(f"Created project: {project_dir.name}", "success")
    return redirect(url_for("index", project=project_dir.name))


@app.post("/projects/rename")
def rename_project():
    current_name = request.form.get("current_name")
    new_name = request.form.get("new_name")

    current_dir = _project_dir(current_name)
    safe_new_name = _normalize_project_name(new_name)

    if current_dir is None:
        flash("Project not found.", "error")
        return redirect(url_for("index"))

    if not safe_new_name:
        flash("Enter a valid project name.", "error")
        return redirect(url_for("index", project=current_dir.name))

    target_dir = OUTPUT_ROOT / safe_new_name
    if target_dir.exists():
        flash("A project with that name already exists.", "error")
        return redirect(url_for("index", project=current_dir.name))

    current_dir.rename(target_dir)
    flash(f"Renamed project to: {target_dir.name}", "success")
    return redirect(url_for("index", project=target_dir.name))


@app.post("/projects/delete")
def delete_project():
    project_name = request.form.get("project_name")
    project_dir = _project_dir(project_name)

    if project_dir is None:
        flash("Project not found.", "error")
        return redirect(url_for("index"))

    shutil.rmtree(project_dir)
    flash(f"Deleted project: {project_name}", "success")

    projects = _list_projects()
    if not projects:
        new_project = _create_project()
        return redirect(url_for("index", project=new_project.name))

    return redirect(url_for("index", project=projects[0]["name"]))


@app.post("/generate")
def generate():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    raw_text = request.form.get("source_text") or ""
    project_name = _normalize_project_name(request.form.get("project_name"))
    uploaded_images = request.files.getlist("images")

    has_image = any((f.filename or "").strip() for f in uploaded_images)
    if not raw_text.strip() and not has_image:
        flash("Add text or at least one image before generating.", "error")
        return redirect(url_for("index", project=project_name))

    try:
        project_dir = _create_project(project_name)
        export_dir, copied_count = _create_export(project_dir, raw_text, uploaded_images)
        zip_path = _zip_export(export_dir)
    except OSError as error:
        app.logger.exception("Failed to prepare export")
        flash(f"Failed to prepare export: {error}", "error")
        return redirect(url_for("index", project=project_name))

    @after_this_request
    def cleanup_generated_zip(response):
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            app.logger.warning("Failed to remove temporary ZIP: %s", zip_path)
        return response

    flash(
        f"Project saved: {export_dir.name}. Images copied: {copied_count}. "
        f"Directory path: {export_dir}",
        "success",
    )
    response = send_file(zip_path, as_attachment=True, download_name=f"{export_dir.name}.zip")
    response.headers["X-Project-Name"] = export_dir.name
    return response


@app.post("/save")
def save_project():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    raw_text = request.form.get("source_text") or ""
    project_name = _normalize_project_name(request.form.get("project_name"))
    uploaded_images = request.files.getlist("images")

    project_dir = _create_project(project_name)
    _, copied_count = _create_export(project_dir, raw_text, uploaded_images)

    flash(
        f"Progress saved for {project_dir.name}. Images copied: {copied_count}.",
        "success",
    )
    return redirect(url_for("index", project=project_dir.name))


@app.post("/preview")
def preview_project():
    raw_text = request.form.get("source_text") or ""
    project_name = _normalize_project_name(request.form.get("project_name"))

    if not raw_text.strip() and project_name:
        project_dir = _project_dir(project_name)
        if project_dir is not None:
            raw_text = _load_project_content(project_dir)

    rendered_html = _render_markdown_html(raw_text, project_name)
    return render_template(
        "preview.html",
        rendered_html=rendered_html,
        project_name=project_name or "Unsaved Preview",
        auto_refresh=False,
        refresh_url=None,
    )


@app.get("/preview/saved")
def preview_saved_project():
    project_name = _normalize_project_name(request.args.get("project"))
    if not project_name:
        flash("Pick a project before opening preview.", "error")
        return redirect(url_for("index"))

    project_dir = _project_dir(project_name)
    if project_dir is None:
        flash("Project not found for preview.", "error")
        return redirect(url_for("index"))

    raw_text = _load_project_content(project_dir)
    rendered_html = _render_markdown_html(raw_text, project_name)
    return render_template(
        "preview.html",
        rendered_html=rendered_html,
        project_name=project_name,
        auto_refresh=True,
        refresh_url=url_for("preview_saved_project_content", project=project_name),
    )


@app.get("/preview/saved/content")
def preview_saved_project_content():
    project_name = _normalize_project_name(request.args.get("project"))
    if not project_name:
        return jsonify({"error": "Missing project name"}), 400

    project_dir = _project_dir(project_name)
    if project_dir is None:
        return jsonify({"error": "Project not found"}), 404

    raw_text = _load_project_content(project_dir)
    rendered_html = _render_markdown_html(raw_text, project_name)
    return jsonify({"rendered_html": rendered_html})


@app.get("/documentation")
def documentation_page():
    if not README_PATH.exists():
        flash("README.md not found.", "error")
        return redirect(url_for("index"))

    readme_text = README_PATH.read_text(encoding="utf-8")
    rendered_html = _render_markdown_html(readme_text, None)
    return render_template(
        "preview.html",
        rendered_html=rendered_html,
        project_name="Documentation",
        auto_refresh=False,
        refresh_url=None,
    )


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=8000)
