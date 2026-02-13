"""Unit tests for Perspective Pydantic models."""

from __future__ import annotations

from ignition_cli.models.perspective import (
    ComponentMeta,
    PageConfig,
    PerspectiveComponent,
    PerspectiveView,
    ResourceMeta,
    StyleClass,
    ViewProps,
)


class TestComponentMeta:
    def test_defaults(self):
        m = ComponentMeta(name="root")
        assert m.name == "root"
        assert m.hasDelegate is False

    def test_with_delegate(self):
        m = ComponentMeta(name="root", hasDelegate=True)
        assert m.hasDelegate is True


class TestViewProps:
    def test_defaults(self):
        p = ViewProps()
        assert p.defaultSize == {"width": 800, "height": 600}

    def test_custom_size(self):
        p = ViewProps(defaultSize={"width": 1024, "height": 768})
        assert p.defaultSize["width"] == 1024


class TestPerspectiveComponent:
    def test_minimal(self):
        c = PerspectiveComponent(
            type="ia.container.flex",
            meta=ComponentMeta(name="root"),
        )
        assert c.type == "ia.container.flex"
        assert c.meta.name == "root"
        assert c.children == []
        assert c.props == {}

    def test_with_children(self):
        child = PerspectiveComponent(
            type="ia.display.label",
            meta=ComponentMeta(name="label1"),
            props={"text": "Hello"},
        )
        parent = PerspectiveComponent(
            type="ia.container.flex",
            meta=ComponentMeta(name="root"),
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].props["text"] == "Hello"


class TestPerspectiveView:
    def test_minimal(self):
        view = PerspectiveView(
            root=PerspectiveComponent(
                type="ia.container.flex",
                meta=ComponentMeta(name="root"),
            ),
        )
        assert view.root.type == "ia.container.flex"
        assert view.params == {}
        assert view.custom == {}

    def test_from_dict(self):
        data = {
            "root": {
                "type": "ia.container.flex",
                "meta": {"name": "root"},
                "props": {"direction": "column"},
                "children": [
                    {
                        "type": "ia.display.label",
                        "meta": {"name": "title"},
                        "props": {"text": "Hello"},
                    }
                ],
            },
            "props": {"defaultSize": {"width": 1200, "height": 800}},
            "params": {"id": None},
        }
        view = PerspectiveView.model_validate(data)
        assert view.root.props["direction"] == "column"
        assert len(view.root.children) == 1
        assert view.props.defaultSize["width"] == 1200
        assert "id" in view.params

    def test_roundtrip(self):
        view = PerspectiveView(
            root=PerspectiveComponent(
                type="ia.container.flex",
                meta=ComponentMeta(name="root"),
            ),
            props=ViewProps(defaultSize={"width": 500, "height": 400}),
        )
        data = view.model_dump(mode="json")
        view2 = PerspectiveView.model_validate(data)
        assert view2.root.type == view.root.type
        assert view2.props.defaultSize == view.props.defaultSize


class TestResourceMeta:
    def test_defaults(self):
        r = ResourceMeta(files=["view.json"])
        assert r.scope == "G"
        assert r.version == 1
        assert r.restricted is False
        assert r.overridable is True
        assert r.files == ["view.json"]


class TestStyleClass:
    def test_minimal(self):
        s = StyleClass()
        assert s.base == {}

    def test_with_styles(self):
        s = StyleClass(
            base={"style": {"backgroundColor": "#007bff", "color": "white"}}
        )
        assert s.base["style"]["backgroundColor"] == "#007bff"


class TestPageConfig:
    def test_minimal(self):
        p = PageConfig()
        assert p.pages == {}

    def test_with_pages(self):
        p = PageConfig(
            pages={
                "/": {"viewPath": "Home/Main"},
                "/settings": {"viewPath": "Settings/Main"},
            }
        )
        assert len(p.pages) == 2
        assert p.pages["/"]["viewPath"] == "Home/Main"
