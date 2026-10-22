from __future__ import annotations

from typing import Optional

import typer
from rich import print as rprint
from ._version import __version__

from .ai.prompts import PROVIDER_REGISTRY
from .config import load_config, redacted_config, save_config
from .session import list_sessions

app = typer.Typer(
    name="echo",
    help="Terminal AI coding assistant with a beautiful TUI",
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


def _version_callback(value: bool):
    if value:
        rprint(f"[bold #cba6f7]Echo[/bold #cba6f7] v{__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version",
        callback=_version_callback,
        is_eager=True,
    ),
):
    pass


@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="One-shot query (skip TUI)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
):
    """Start Echo TUI or run a one-shot query."""
    if message:
        _run_one_shot(message, provider, model)
    else:
        from .tui import EchoApp
        app = EchoApp()
        app.run()


def _run_one_shot(query: str, provider_name: Optional[str] = None, model_name: Optional[str] = None):
    import asyncio

    config = load_config()
    if provider_name:
        config["ai"]["provider"] = provider_name
    if model_name:
        config["ai"]["model"] = model_name

    from .ai.provider import create_provider
    from .ai.prompts import SYSTEM_PROMPTS
    from .config import get_provider_config

    provider_config = get_provider_config(config)
    provider = create_provider(provider_config)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS["default"]},
        {"role": "user", "content": query},
    ]

    async def run():
        from rich.console import Console
        console = Console()
        console.print(f"\n[bold #a6e3a1]Echo[/bold #a6e3a1]\n")
        async for chunk in provider.chat_stream(messages):
            console.print(chunk, end="")
        console.print()

    asyncio.run(run())


@app.command()
def sessions():
    """List saved sessions."""
    sessions = list_sessions()
    if not sessions:
        rprint("[dim]No saved sessions.[/dim]")
        return
    rprint("[bold]Saved Sessions:[/bold]")
    for s in sessions:
        rprint(f"  [green]{s}[/green]")


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key, e.g. ai.api_key"),
    value: Optional[str] = typer.Argument(None, help="Value to set"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current config"),
):
    """Manage Echo configuration."""
    current = load_config()

    if show:
        import yaml
        rprint("[bold]Echo Configuration:[/bold]")
        rprint(yaml.safe_dump(redacted_config(current), default_flow_style=False, allow_unicode=True))
        return

    if key and value:
        parts = key.split(".")
        target = current
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        save_config(current)
        masked = "****" if "key" in key.lower() or "secret" in key.lower() else value
        rprint(f"[green]Set {key} = {masked}[/green]")
        return

    if not key and not value:
        import yaml
        rprint("[bold]Echo Configuration:[/bold]")
        rprint(yaml.safe_dump(redacted_config(load_config()), default_flow_style=False, allow_unicode=True))
        return

    rprint("[yellow]Usage: echo config <key> <value> or echo config --show[/yellow]")


@app.command()
def providers():
    """List all supported AI providers and models."""
    rprint("[bold]Supported AI Providers:[/bold]")
    for key, cfg in PROVIDER_REGISTRY.items():
        name = cfg["name"]
        models = ", ".join(cfg["models"][:5])
        extra = f" +{len(cfg['models'])-5} more" if len(cfg['models']) > 5 else ""
        rprint(f"\n[bold cyan]{name}[/bold cyan] [dim]({key})[/dim]")
        rprint(f"  Models: [green]{models}{extra}[/green]")
        rprint(f"  Docs:   [blue]{cfg['docs']}[/blue]")


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
):
    """Launch the Echo Web UI."""
    import uvicorn

    if host not in ("127.0.0.1", "localhost", "::1"):
        raise typer.BadParameter("Echo Web supports loopback hosts only; remote authentication is not implemented.")

    rprint(f"[bold #d97757]echo web[/bold #d97757] → http://{host}:{port}")
    uvicorn.run("echo.web:app", host=host, port=port, reload=False, log_level="warning")



def run_tui():
    from .tui import EchoApp
    app = EchoApp()
    app.run()


if __name__ == "__main__":
    app()
