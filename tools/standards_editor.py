#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Local WYSIWYG-ish Markdown editor for the OpenRai Standards repo."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = REPO_ROOT / "static"
NODE_MODULES_ROOT = STATIC_ROOT / "scripts" / "vendor" / "node_modules"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8008
MAX_SAVE_BYTES = 10 * 1024 * 1024


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenRai Standards Editor</title>
  <link rel="stylesheet" href="/static/scripts/vendor/node_modules/@toast-ui/editor/dist/toastui-editor.css">
  <style>
    :root {
      color-scheme: light;
      --border: #d7dee8;
      --panel: #f6f8fb;
      --ink: #17202a;
      --muted: #5c6b7a;
      --accent: #0b6bcb;
      --accent-dark: #064f97;
      --danger: #a4382a;
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      height: 100%;
      overflow: hidden;
    }

    body {
      margin: 0;
      color: var(--ink);
      background: #ffffff;
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .app {
      display: grid;
      grid-template-columns: minmax(220px, 280px) 1fr;
      height: 100vh;
      overflow: hidden;
    }

    aside {
      border-right: 1px solid var(--border);
      background: var(--panel);
      min-width: 0;
      overflow: auto;
      padding: 14px;
    }

    main {
      min-width: 0;
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      height: 100vh;
      overflow: hidden;
    }

    .brand {
      font-size: 15px;
      font-weight: 700;
      margin: 0 0 12px;
    }

    .file-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .file-button {
      width: 100%;
      border: 1px solid transparent;
      border-radius: 6px;
      background: transparent;
      color: var(--ink);
      cursor: pointer;
      display: block;
      font: inherit;
      overflow-wrap: anywhere;
      padding: 7px 8px;
      text-align: left;
    }

    .file-button:hover {
      background: #ffffff;
      border-color: var(--border);
    }

    .file-button.active {
      background: #e7f1ff;
      border-color: #9cc8f5;
      color: #073f78;
      font-weight: 650;
    }

    .toolbar {
      align-items: center;
      border-bottom: 1px solid var(--border);
      display: flex;
      gap: 10px;
      min-width: 0;
      padding: 10px 14px;
    }

    .path {
      flex: 1;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .status {
      color: var(--muted);
      min-width: 130px;
      text-align: right;
      white-space: nowrap;
    }

    .status.error {
      color: var(--danger);
    }

    .mode-toggle {
      border: 1px solid var(--border);
      border-radius: 6px;
      display: inline-flex;
      overflow: hidden;
    }

    .mode-toggle button {
      background: #ffffff;
      border: 0;
      border-right: 1px solid var(--border);
      color: var(--muted);
      cursor: pointer;
      font: inherit;
      font-weight: 650;
      min-width: 86px;
      padding: 7px 10px;
    }

    .mode-toggle button:last-child {
      border-right: 0;
    }

    .mode-toggle button.active {
      background: #edf5ff;
      box-shadow: inset 0 0 0 1px #79aee3;
      color: #155f9e;
    }

    .mode-toggle button:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }

    button.save {
      background: var(--accent);
      border: 1px solid var(--accent-dark);
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      padding: 7px 12px;
    }

    button.save:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }

    #editor {
      min-width: 0;
      min-height: 0;
      overflow: hidden;
    }

    #editor .toastui-editor-defaultUI {
      height: 100% !important;
    }

    #editor .toastui-editor-mode-switch,
    #editor .toastui-editor-md-tab-container,
    #editor .toastui-editor-mode-switch-tab,
    #editor .toastui-editor-md-tab,
    #editor .toastui-editor-ww-tab {
      display: none !important;
      height: 0 !important;
      min-height: 0 !important;
      overflow: hidden !important;
    }

    .lint-panel {
      background: #fff7f5;
      border-bottom: 0;
      color: var(--danger);
      display: block;
      font-size: 14px;
      height: 0;
      line-height: 1.45;
      overflow: hidden;
      padding: 0 14px;
    }

    .lint-panel.visible {
      border-bottom: 1px solid #f0b7ae;
      height: auto;
      padding: 10px 14px;
    }

    .lint-panel strong {
      display: block;
      margin-bottom: 4px;
    }

    .lint-panel ul {
      margin: 0;
      padding-left: 22px;
    }

    .lint-panel li {
      margin: 2px 0;
    }

    .lint-jump {
      background: transparent;
      border: 0;
      color: var(--danger);
      cursor: pointer;
      font: inherit;
      padding: 0;
      text-align: left;
      text-decoration: underline;
      text-underline-offset: 2px;
    }

    .lint-jump:hover {
      color: #7f241b;
    }

    #editor .lint-target-line {
      background: #fff3b8;
      box-shadow: inset 3px 0 0 #d49b00;
    }

    #editor .toastui-editor-contents,
    #editor .toastui-editor-contents p,
    #editor .toastui-editor-contents li,
    #editor .toastui-editor-contents blockquote {
      font-size: 16px;
      line-height: 1.6;
    }

    #editor .toastui-editor-contents {
      color: #24292f;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    }

    #editor .toastui-editor-contents pre,
    #editor .toastui-editor-contents code {
      font-size: 14px;
      line-height: 1.55;
    }

    #editor .toastui-editor-contents h1 {
      font-size: 2em;
    }

    #editor .toastui-editor-contents h2 {
      font-size: 1.5em;
    }

    #editor .toastui-editor-contents h3 {
      font-size: 1.25em;
    }

    .empty {
      color: var(--muted);
      padding: 24px;
    }

    @media (max-width: 760px) {
      .app {
        grid-template-columns: 1fr;
        grid-template-rows: auto 1fr;
      }

      aside {
        border-bottom: 1px solid var(--border);
        border-right: 0;
        max-height: 36vh;
        overflow: auto;
      }

      main {
        min-height: 64vh;
        grid-template-rows: auto auto minmax(0, 1fr);
      }

      .toolbar {
        flex-wrap: wrap;
      }

      .status {
        text-align: left;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1 class="brand">Standards Editor</h1>
      <div id="files" class="file-list" aria-label="Markdown files"></div>
    </aside>
    <main>
      <div class="toolbar">
        <div id="current-path" class="path">No file selected</div>
        <div class="mode-toggle" role="group" aria-label="Editor mode">
          <button id="mode-markdown" type="button" disabled>Markdown</button>
          <button id="mode-wysiwyg" type="button" class="active" disabled>WYSIWYG</button>
        </div>
        <button id="save" class="save" disabled>Save</button>
        <div id="status" class="status">Loading files...</div>
      </div>
      <div id="lint-panel" class="lint-panel" role="alert" aria-live="polite"></div>
      <div id="editor" class="empty">Select a Markdown file.</div>
    </main>
  </div>

  <script type="importmap">__IMPORT_MAP__</script>
  <script type="module" src="/static/scripts/standards-editor.js"></script>
</body>
</html>
"""


class StandardsEditorHandler(BaseHTTPRequestHandler):
    server_version = "StandardsEditor/1.0"

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = index_html_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if parsed.path.startswith("/static/"):
            static_path = self.resolve_static_path(parsed.path)
            if static_path is None:
                return
            self.send_static_headers(static_path)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_bytes(index_html_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            static_path = self.resolve_static_path(parsed.path)
            if static_path is None:
                return
            self.send_static_file(static_path)
            return
        if parsed.path == "/api/files":
            self.send_json({"files": list_markdown_files()})
            return
        if parsed.path == "/api/file":
            path = self.query_path(parsed.query)
            if path is None:
                return
            self.send_json({"path": path.relative_to(REPO_ROOT).as_posix(), "content": path.read_text(encoding="utf-8")})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/file":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        path = self.query_path(parsed.query)
        if path is None:
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self.send_error_json(HTTPStatus.LENGTH_REQUIRED, "Content-Length required")
            return

        try:
            length = int(content_length)
        except ValueError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
            return

        if length > MAX_SAVE_BYTES:
            self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "File is too large")
            return

        body = self.rfile.read(length)
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Content must be UTF-8")
            return

        path.write_text(text, encoding="utf-8")
        self.send_json({"ok": True, "path": path.relative_to(REPO_ROOT).as_posix()})
        print(f"Save {path.relative_to(REPO_ROOT).as_posix()} ({length} bytes)", flush=True)

    def query_path(self, query: str) -> Path | None:
        values = parse_qs(query).get("path", [])
        if len(values) != 1:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Expected one path parameter")
            return None

        try:
            return resolve_markdown_path(values[0])
        except ValueError as error:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(error))
            return None

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_bytes(body, "application/json; charset=utf-8", status)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message}, status)

    def send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_static_headers(self, path: Path) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for_path(path))
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def send_static_file(self, path: Path) -> None:
        self.send_static_headers(path)
        with path.open("rb") as file:
            self.wfile.write(file.read())

    def resolve_static_path(self, request_path: str) -> Path | None:
        raw_path = request_path.removeprefix("/static/")
        if not raw_path or raw_path.startswith("/") or raw_path.startswith("\\"):
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return None

        candidate = (STATIC_ROOT / raw_path).resolve()
        try:
            candidate.relative_to(STATIC_ROOT)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return None

        if not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return None
        return candidate

    def log_message(self, format: str, *args: object) -> None:
        return


def index_html_bytes() -> bytes:
    html = INDEX_HTML.replace("__IMPORT_MAP__", build_import_map_json())
    return html.encode("utf-8")


def build_import_map_json() -> str:
    imports: dict[str, str] = {}
    for package_json in sorted(NODE_MODULES_ROOT.glob("*/package.json")):
        add_package_imports(imports, package_json.parent)
    for package_json in sorted(NODE_MODULES_ROOT.glob("@*/*/package.json")):
        add_package_imports(imports, package_json.parent)
    imports["extend"] = "/static/scripts/vendor-shims/extend.js"
    imports["pluralize"] = "/static/scripts/vendor-shims/pluralize.js"
    return json.dumps({"imports": imports}, indent=4, sort_keys=True)


def add_package_imports(imports: dict[str, str], package_root: Path) -> None:
    metadata = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
    name = metadata.get("name")
    if not isinstance(name, str):
        return

    entry = package_entrypoint(metadata, package_root)
    imports[name] = static_url(package_root / entry)
    imports[f"{name}/"] = static_url(package_root) + "/"
    add_package_export_imports(imports, metadata, package_root, name)
    add_package_internal_imports(imports, metadata, package_root)


def add_package_export_imports(
    imports: dict[str, str], metadata: dict[str, object], package_root: Path, package_name: str
) -> None:
    exports = metadata.get("exports")
    if not isinstance(exports, dict):
        return

    for subpath, target in exports.items():
        if not isinstance(subpath, str) or subpath == "." or "*" in subpath:
            continue
        if not subpath.startswith("./"):
            continue

        export_target = conditional_export_target(target)
        if export_target is None:
            continue
        imports[f"{package_name}/{subpath.removeprefix('./')}"] = static_url(
            package_root / normalize_package_entrypoint(export_target, package_root)
        )


def conditional_export_target(target: object) -> str | None:
    if isinstance(target, str):
        return target
    if isinstance(target, dict):
        value = target.get("browser") or target.get("import") or target.get("default")
        if isinstance(value, str):
            return value
    return None


def add_package_internal_imports(imports: dict[str, str], metadata: dict[str, object], package_root: Path) -> None:
    package_imports = metadata.get("imports")
    if not isinstance(package_imports, dict):
        return

    for specifier, target in package_imports.items():
        if not isinstance(specifier, str):
            continue
        if isinstance(target, str):
            imports[specifier] = static_url(package_root / normalize_package_entrypoint(target, package_root))
        elif isinstance(target, dict):
            browser_target = target.get("browser") or target.get("default")
            if isinstance(browser_target, str):
                imports[specifier] = static_url(package_root / normalize_package_entrypoint(browser_target, package_root))


def package_entrypoint(metadata: dict[str, object], package_root: Path) -> str:
    exports = metadata.get("exports")
    if isinstance(exports, str):
        return normalize_package_entrypoint(exports, package_root)
    if isinstance(exports, dict):
        root_export = exports.get(".")
        if isinstance(root_export, str):
            return normalize_package_entrypoint(root_export, package_root)
        if isinstance(root_export, dict):
            import_export = root_export.get("import") or root_export.get("default")
            if isinstance(import_export, str):
                return normalize_package_entrypoint(import_export, package_root)
        root_condition = exports.get("browser") or exports.get("default")
        if isinstance(root_condition, str):
            return normalize_package_entrypoint(root_condition, package_root)

    for key in ("module", "browser", "main"):
        value = metadata.get(key)
        if isinstance(value, str):
            return normalize_package_entrypoint(value, package_root)
    return "index.js"


def normalize_package_entrypoint(entry: str, package_root: Path) -> str:
    normalized = entry.removeprefix("./")
    candidate = package_root / normalized
    if candidate.is_file():
        return normalized
    if not Path(normalized).suffix and candidate.with_suffix(".js").is_file():
        return f"{normalized}.js"
    if (candidate / "index.js").is_file():
        return f"{normalized}/index.js"
    return normalized


def static_url(path: Path) -> str:
    return "/" + path.relative_to(REPO_ROOT).as_posix()


def content_type_for_path(path: Path) -> str:
    if path.suffix == ".js":
        return "text/javascript; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".json":
        return "application/json; charset=utf-8"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def list_markdown_files() -> list[dict[str, str]]:
    paths = [REPO_ROOT / "README.md"]
    rfcs_dir = REPO_ROOT / "rfcs"
    if rfcs_dir.is_dir():
        paths.extend(sorted(rfcs_dir.glob("*.md"), key=lambda path: path.name.lower()))

    files = []
    for path in paths:
        if path.is_file():
            files.append({"path": path.relative_to(REPO_ROOT).as_posix()})
    return files


def resolve_markdown_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Path is required")
    if raw_path.startswith("/") or raw_path.startswith("\\"):
        raise ValueError("Absolute paths are not allowed")

    candidate = (REPO_ROOT / raw_path).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as error:
        raise ValueError("Path must stay inside the repository") from error

    if candidate.suffix.lower() != ".md":
        raise ValueError("Only Markdown files can be edited")
    if not candidate.is_file():
        raise ValueError("Markdown file does not exist")
    if candidate != REPO_ROOT / "README.md" and candidate.parent != REPO_ROOT / "rfcs":
        raise ValueError("Only README.md and rfcs/*.md can be edited")
    return candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local Standards Markdown editor BFF. "
            "Start with: uv run tools/standards_editor.py"
        )
    )
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help=f"port to bind, default {DEFAULT_PORT}")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mimetypes.add_type("text/markdown", ".md")
    server = ThreadingHTTPServer((DEFAULT_HOST, args.port), StandardsEditorHandler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print("OpenRai Standards Editor BFF", flush=True)
    print(f"Local URL: {url}", flush=True)
    print("Press Ctrl-C to stop. Save HTTP actions will be logged below.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    main()
