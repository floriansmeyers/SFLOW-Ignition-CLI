"""Integration tests for perspective commands — view, page, style, session."""

from __future__ import annotations

import io
import json
import zipfile

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()
GW = "https://gw:8043"
BASE = f"{GW}/data/api/v1"
COMMON_OPTS = ["--url", GW, "--token", "k:s"]
PERSPECTIVE = "com.inductiveautomation.perspective"

# Reusable minimal view data to avoid long lines
_FLEX_ROOT = {
    "root": {
        "type": "ia.container.flex",
        "meta": {"name": "root"},
    },
}


def _make_project_zip(
    views: dict[str, dict] | None = None,
    styles: dict[str, dict] | None = None,
    page_config: dict | None = None,
    session_props: dict | None = None,
) -> bytes:
    """Build a minimal project zip with Perspective resources."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("project.json", json.dumps({
            "title": "Test",
            "enabled": True,
            "inheritable": False,
        }))
        resource_json = json.dumps({
            "scope": "G", "version": 1, "restricted": False,
            "overridable": True, "files": ["view.json"],
            "attributes": {},
        })
        for path, view_data in (views or {}).items():
            zf.writestr(
                f"{PERSPECTIVE}/views/{path}/view.json",
                json.dumps(view_data),
            )
            zf.writestr(
                f"{PERSPECTIVE}/views/{path}/resource.json",
                resource_json,
            )
        style_resource = json.dumps({
            "scope": "G", "version": 1, "restricted": False,
            "overridable": True, "files": ["style.json"],
            "attributes": {},
        })
        for name, style_data in (styles or {}).items():
            zf.writestr(
                f"{PERSPECTIVE}/style-classes/{name}/style.json",
                json.dumps(style_data),
            )
            zf.writestr(
                f"{PERSPECTIVE}/style-classes/{name}/resource.json",
                style_resource,
            )
        if page_config is not None:
            zf.writestr(
                f"{PERSPECTIVE}/page-config/config.json",
                json.dumps(page_config),
            )
            zf.writestr(
                f"{PERSPECTIVE}/page-config/resource.json",
                json.dumps({
                    "scope": "G", "version": 1, "restricted": False,
                    "overridable": True, "files": ["config.json"],
                    "attributes": {},
                }),
            )
        if session_props is not None:
            zf.writestr(
                f"{PERSPECTIVE}/session-props/props.json",
                json.dumps(session_props),
            )
            zf.writestr(
                f"{PERSPECTIVE}/session-props/resource.json",
                json.dumps({
                    "scope": "G", "version": 1, "restricted": False,
                    "overridable": True, "files": ["props.json"],
                    "attributes": {},
                }),
            )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# View commands
# ---------------------------------------------------------------------------


class TestViewList:
    @respx.mock
    def test_view_list(self):
        zip_bytes = _make_project_zip(views={
            "Home": _FLEX_ROOT,
            "Settings/Main": _FLEX_ROOT,
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "list", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Home" in result.output
        assert "Settings/Main" in result.output

    @respx.mock
    def test_view_list_json(self):
        zip_bytes = _make_project_zip(views={
            "Home": _FLEX_ROOT,
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "list", "MyApp", "-f", "json", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Home" in result.output

    @respx.mock
    def test_view_list_empty(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "list", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0


class TestViewShow:
    @respx.mock
    def test_view_show(self):
        view_data = {
            "root": {"type": "ia.container.flex", "meta": {"name": "root"},
                     "props": {"direction": "column"}},
            "props": {"defaultSize": {"width": 800, "height": 600}},
        }
        zip_bytes = _make_project_zip(views={"Home": view_data})
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "show", "MyApp", "Home", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "ia.container.flex" in result.output

    @respx.mock
    def test_view_show_not_found(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "show", "MyApp", "NoSuchView", *COMMON_OPTS,
        ])
        assert result.exit_code != 0


class TestViewCreate:
    @respx.mock
    def test_view_create(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        view_json = json.dumps({
            "root": {"type": "ia.container.flex", "meta": {"name": "root"}},
        })
        result = runner.invoke(app, [
            "perspective", "view", "create", "MyApp", "NewView",
            "--json", view_json, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_view_create_already_exists(self):
        zip_bytes = _make_project_zip(views={
            "ExistingView": _FLEX_ROOT,
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        view_json = json.dumps({
            "root": {"type": "ia.container.flex", "meta": {"name": "root"}},
        })
        result = runner.invoke(app, [
            "perspective", "view", "create", "MyApp", "ExistingView",
            "--json", view_json, *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "already exists" in result.output

    @respx.mock
    def test_view_create_nested(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        view_json = json.dumps({
            "root": {"type": "ia.container.flex", "meta": {"name": "root"}},
        })
        result = runner.invoke(app, [
            "perspective", "view", "create", "MyApp", "Folder/SubView",
            "--json", view_json, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_view_create_from_file(self, tmp_path):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        view_file = tmp_path / "view.json"
        view_file.write_text(json.dumps({
            "root": {"type": "ia.container.flex", "meta": {"name": "root"}},
        }))
        result = runner.invoke(app, [
            "perspective", "view", "create", "MyApp", "FileView",
            "--json", f"@{view_file}", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "created" in result.output


class TestViewUpdate:
    @respx.mock
    def test_view_update(self):
        zip_bytes = _make_project_zip(views={
            "Home": _FLEX_ROOT,
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        new_json = json.dumps({
            "root": {"type": "ia.container.flex", "meta": {"name": "root"},
                     "props": {"direction": "row"}},
        })
        result = runner.invoke(app, [
            "perspective", "view", "update", "MyApp", "Home",
            "--json", new_json, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output

    @respx.mock
    def test_view_update_not_found(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        new_json = json.dumps({
            "root": {"type": "ia.container.flex", "meta": {"name": "root"}},
        })
        result = runner.invoke(app, [
            "perspective", "view", "update", "MyApp", "Missing",
            "--json", new_json, *COMMON_OPTS,
        ])
        assert result.exit_code != 0


class TestViewDelete:
    @respx.mock
    def test_view_delete(self):
        zip_bytes = _make_project_zip(views={
            "OldView": _FLEX_ROOT,
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, [
            "perspective", "view", "delete", "MyApp", "OldView",
            "--force", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "deleted" in result.output

    @respx.mock
    def test_view_delete_not_found(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "delete", "MyApp", "NoSuchView",
            "--force", *COMMON_OPTS,
        ])
        assert result.exit_code != 0


class TestViewTree:
    @respx.mock
    def test_view_tree(self):
        zip_bytes = _make_project_zip(views={
            "Home": _FLEX_ROOT,
            "Settings/Main": _FLEX_ROOT,
            "Settings/Advanced": _FLEX_ROOT,
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "view", "tree", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Home" in result.output
        assert "Settings" in result.output
        assert "Main" in result.output
        assert "Advanced" in result.output


# ---------------------------------------------------------------------------
# Page commands
# ---------------------------------------------------------------------------


class TestPageList:
    @respx.mock
    def test_page_list(self):
        zip_bytes = _make_project_zip(page_config={
            "pages": {
                "/": {"viewPath": "Home/Main"},
                "/settings": {"viewPath": "Settings/Main"},
            }
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "page", "list", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Home/Main" in result.output
        assert "/settings" in result.output


class TestPageShow:
    @respx.mock
    def test_page_show(self):
        zip_bytes = _make_project_zip(page_config={
            "pages": {"/": {"viewPath": "Home/Main"}}
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "page", "show", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Home/Main" in result.output


class TestPageUpdate:
    @respx.mock
    def test_page_update(self):
        zip_bytes = _make_project_zip(page_config={
            "pages": {"/": {"viewPath": "Home/Main"}}
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        new_config = json.dumps({
            "pages": {
                "/": {"viewPath": "Home/NewMain"},
                "/new": {"viewPath": "NewPage"},
            }
        })
        result = runner.invoke(app, [
            "perspective", "page", "update", "MyApp",
            "--json", new_config, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output


# ---------------------------------------------------------------------------
# Style commands
# ---------------------------------------------------------------------------


class TestStyleList:
    @respx.mock
    def test_style_list(self):
        zip_bytes = _make_project_zip(styles={
            "my-button": {"base": {"style": {"color": "blue"}}},
            "my-card": {"base": {"style": {"borderRadius": "8px"}}},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "style", "list", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "my-button" in result.output
        assert "my-card" in result.output


class TestStyleShow:
    @respx.mock
    def test_style_show(self):
        zip_bytes = _make_project_zip(styles={
            "my-button": {"base": {"style": {"backgroundColor": "#007bff"}}},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "style", "show", "MyApp", "my-button", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "#007bff" in result.output


class TestStyleCreate:
    @respx.mock
    def test_style_create(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        style_json = json.dumps({"base": {"style": {"color": "red"}}})
        result = runner.invoke(app, [
            "perspective", "style", "create", "MyApp", "new-style",
            "--json", style_json, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_style_create_already_exists(self):
        zip_bytes = _make_project_zip(styles={
            "existing": {"base": {"style": {}}},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        style_json = json.dumps({"base": {"style": {"color": "red"}}})
        result = runner.invoke(app, [
            "perspective", "style", "create", "MyApp", "existing",
            "--json", style_json, *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestStyleUpdate:
    @respx.mock
    def test_style_update(self):
        zip_bytes = _make_project_zip(styles={
            "my-button": {"base": {"style": {"color": "blue"}}},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        new_json = json.dumps({"base": {"style": {"color": "red"}}})
        result = runner.invoke(app, [
            "perspective", "style", "update", "MyApp", "my-button",
            "--json", new_json, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output

    @respx.mock
    def test_style_update_not_found(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        new_json = json.dumps({"base": {"style": {"color": "red"}}})
        result = runner.invoke(app, [
            "perspective", "style", "update", "MyApp", "missing",
            "--json", new_json, *COMMON_OPTS,
        ])
        assert result.exit_code != 0


class TestStyleDelete:
    @respx.mock
    def test_style_delete(self):
        zip_bytes = _make_project_zip(styles={
            "old-style": {"base": {"style": {}}},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, [
            "perspective", "style", "delete", "MyApp", "old-style",
            "--force", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------


class TestSessionShow:
    @respx.mock
    def test_session_show(self):
        zip_bytes = _make_project_zip(session_props={
            "custom": {"theme": "dark"},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        result = runner.invoke(app, [
            "perspective", "session", "show", "MyApp", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "dark" in result.output


class TestSessionUpdate:
    @respx.mock
    def test_session_update(self):
        zip_bytes = _make_project_zip(session_props={
            "custom": {"theme": "dark"},
        })
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        respx.post(f"{BASE}/projects/import/MyApp").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        new_json = json.dumps({"custom": {"theme": "light", "lang": "en"}})
        result = runner.invoke(app, [
            "perspective", "session", "update", "MyApp",
            "--json", new_json, *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output

    @respx.mock
    def test_session_update_not_found(self):
        zip_bytes = _make_project_zip()
        respx.get(f"{BASE}/projects/export/MyApp").mock(
            return_value=httpx.Response(200, content=zip_bytes)
        )
        new_json = json.dumps({"custom": {"theme": "light"}})
        result = runner.invoke(app, [
            "perspective", "session", "update", "MyApp",
            "--json", new_json, *COMMON_OPTS,
        ])
        assert result.exit_code != 0
