"""Tests for the DeploymentMode model."""

from ignition_cli.models.mode import DeploymentMode


class TestDeploymentModeModel:
    def test_basic_mode(self):
        m = DeploymentMode(name="dev")
        assert m.name == "dev"
        assert m.title is None
        assert m.description is None
        assert m.resourceCount is None

    def test_mode_with_title_and_description(self):
        m = DeploymentMode(
            name="staging",
            title="Staging",
            description="Pre-production environment",
        )
        assert m.name == "staging"
        assert m.title == "Staging"
        assert m.description == "Pre-production environment"

    def test_mode_with_resource_count(self):
        m = DeploymentMode(name="prod", resourceCount=42)
        assert m.resourceCount == 42

    def test_mode_all_fields(self):
        m = DeploymentMode(
            name="prod",
            title="Production",
            description="Live environment",
            resourceCount=10,
        )
        assert m.name == "prod"
        assert m.title == "Production"
        assert m.description == "Live environment"
        assert m.resourceCount == 10
