"""Config commands — manage gateway profiles."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ignition_cli.client.errors import error_handler
from ignition_cli.config.manager import ConfigManager
from ignition_cli.config.models import GatewayProfile
from ignition_cli.output.formatter import output

app = typer.Typer(name="config", help="Manage gateway profiles and CLI configuration.")
console = Console()


def _get_manager() -> ConfigManager:
    return ConfigManager()


@app.command()
@error_handler
def init() -> None:
    """Interactive setup wizard — create your first gateway profile."""
    mgr = _get_manager()
    console.print("[bold]Ignition CLI Setup Wizard[/]\n")

    name = Prompt.ask("Profile name", default="default")
    url = Prompt.ask("Gateway URL (e.g. https://gateway:8043)")
    token = Prompt.ask("API Token (keyId:secretKey)", default=None)
    verify_ssl = Confirm.ask("Verify SSL certificates?", default=True)

    profile = GatewayProfile(
        name=name,
        url=url.rstrip("/"),
        token=token if token else None,
        verify_ssl=verify_ssl,
    )
    mgr.add_profile(profile)
    console.print(f"\n[green]Profile '{name}' saved and set as default.[/]")
    console.print(f"Config file: {mgr.config_path}")


@app.command()
@error_handler
def add(
    name: Annotated[str, typer.Argument(help="Profile name")],
    url: Annotated[str, typer.Option("--url", "-u", help="Gateway URL")],
    token: Annotated[Optional[str], typer.Option("--token", "-t", help="API token")] = None,
    username: Annotated[Optional[str], typer.Option("--username", help="Basic auth username")] = None,
    password: Annotated[Optional[str], typer.Option("--password", help="Basic auth password")] = None,
    no_verify_ssl: Annotated[bool, typer.Option("--no-verify-ssl", help="Disable SSL verification")] = False,
    set_default: Annotated[bool, typer.Option("--default", help="Set as default profile")] = False,
) -> None:
    """Add a gateway profile."""
    mgr = _get_manager()
    profile = GatewayProfile(
        name=name,
        url=url.rstrip("/"),
        token=token,
        username=username,
        password=password,
        verify_ssl=not no_verify_ssl,
    )
    mgr.add_profile(profile)
    if set_default:
        mgr.set_default(name)
    console.print(f"[green]Profile '{name}' added.[/]")


@app.command("list")
@error_handler
def list_profiles(
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "table",
) -> None:
    """List all configured profiles."""
    mgr = _get_manager()
    profiles = mgr.config.profiles
    if not profiles:
        console.print("[yellow]No profiles configured. Run 'ignition-cli config init' to get started.[/]")
        return

    default = mgr.config.default_profile
    columns = ["Name", "URL", "Auth", "Default"]
    rows = []
    for name, p in profiles.items():
        auth = "token" if p.token else "basic" if p.username else "none"
        is_default = "*" if name == default else ""
        rows.append([name, p.url, auth, is_default])

    output(
        {"profiles": [p.model_dump(exclude_none=True) for p in profiles.values()]},
        fmt,
        columns=columns,
        rows=rows,
        title="Gateway Profiles",
    )


@app.command()
@error_handler
def show(
    name: Annotated[str, typer.Argument(help="Profile name")],
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "table",
) -> None:
    """Show profile details."""
    mgr = _get_manager()
    profile = mgr.get_profile(name)
    if not profile:
        console.print(f"[red]Profile '{name}' not found.[/]")
        raise typer.Exit(1)

    data = profile.model_dump(exclude_none=True)
    # Mask token for display
    if "token" in data:
        data["token"] = data["token"][:8] + "..." if len(data["token"]) > 8 else "***"
    if "password" in data:
        data["password"] = "***"

    output(data, fmt, kv=True, title=f"Profile: {name}")


@app.command("set-default")
@error_handler
def set_default(
    name: Annotated[str, typer.Argument(help="Profile name to set as default")],
) -> None:
    """Set the default gateway profile."""
    mgr = _get_manager()
    if mgr.set_default(name):
        console.print(f"[green]Default profile set to '{name}'.[/]")
    else:
        console.print(f"[red]Profile '{name}' not found.[/]")
        raise typer.Exit(1)


@app.command()
@error_handler
def test(
    name: Annotated[Optional[str], typer.Argument(help="Profile name (uses default if omitted)")] = None,
) -> None:
    """Test connectivity to a gateway."""
    from ignition_cli.client.gateway import GatewayClient

    mgr = _get_manager()
    profile = mgr.resolve_gateway(profile_name=name)
    console.print(f"Testing connection to [bold]{profile.url}[/]...")

    with GatewayClient(profile) as client:
        resp = client.get("/status/info")
        info = resp.json()
        console.print(f"[green]Connected![/] Gateway: {info.get('name', 'Unknown')} v{info.get('version', '?')}")


@app.command()
@error_handler
def remove(
    name: Annotated[str, typer.Argument(help="Profile name to remove")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Remove a gateway profile."""
    mgr = _get_manager()
    if not mgr.get_profile(name):
        console.print(f"[red]Profile '{name}' not found.[/]")
        raise typer.Exit(1)

    if not force:
        if not Confirm.ask(f"Remove profile '{name}'?"):
            console.print("Cancelled.")
            return

    mgr.remove_profile(name)
    console.print(f"[green]Profile '{name}' removed.[/]")
