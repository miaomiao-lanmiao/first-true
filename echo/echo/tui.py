from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Input, RichLog, Static
from rich.cells import cell_len

from .ai.provider import create_provider
from .ai.prompts import PROVIDER_REGISTRY, SYSTEM_PROMPTS
from .config import get_provider_config, load_config
from .session import Session, save_session

ACCENT = "#e8825a"
BG = "#16140f"
BORDER_IDLE = "#2a261f"
TEXT = "#e8e3d8"
DIM = "#6b6559"
DIMMER = "#4a453d"


class EchoApp(App):
    TITLE = "Echo"
    CSS = f"""
    Screen {{ background: {BG}; }}

    #chat-container {{
        height: 1fr;
        overflow-y: auto;
        padding: 1 3;
        background: {BG};
    }}

    #bottom-panel {{
        dock: bottom;
        height: 4;
        margin: 0 1 1 1;
        border: round {BORDER_IDLE};
        background: {BG};
    }}
    #bottom-panel:focus-within {{
        border: round {ACCENT};
    }}

    #chat-input {{
        background: {BG};
        color: {TEXT};
        border: none;
        padding: 0 1;
        height: 3;
        dock: top;
    }}
    #chat-input:focus {{ border: none; }}

    #status-bar {{
        height: 1;
        padding: 0 1;
        background: {BG};
        color: {DIM};
        dock: bottom;
    }}
    #status-bar .dot {{ color: {ACCENT}; }}
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit"),
        Binding("ctrl+n", "new_session", "new"),
        Binding("ctrl+l", "clear", "clear"),
    ]

    def __init__(self):
        super().__init__()
        self.config = load_config()
        provider_config = get_provider_config(self.config)
        self.provider = create_provider(provider_config)
        self.session = Session()

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-container", highlight=True, markup=True, wrap=True)
        yield Container(
            Input(placeholder="Ask Echo anything…", id="chat-input"),
            Static(self._status_text(), id="status-bar"),
            id="bottom-panel",
        )

    def on_mount(self):
        chat = self.query_one("#chat-container", RichLog)
        chat.min_width = chat.content_size.width or (self.size.width - 6)
        chat.write(self._welcome_text(chat.min_width))
        self.query_one("#chat-input", Input).focus()

    def on_resize(self):
        chat = self.query_one("#chat-container", RichLog)
        chat.min_width = chat.content_size.width or (self.size.width - 6)

    def _header_line(self, width: int) -> str:
        left = "echo"
        right = "懒喵大王制作"
        pad = width - cell_len(left) - cell_len(right)
        space = " " * max(1, pad)
        return f"[bold {TEXT}]{left}[/]{space}[{DIMMER}]{right}[/]"

    def _welcome_text(self, width: int) -> str:
        rule = "─" * max(1, width)
        return (
            f"{self._header_line(width)}\n"
            f"[{DIMMER}]{rule}[/{DIMMER}]\n\n"
            f"  [bold {TEXT}]echo[/bold {TEXT}]  [dim]terminal ai coding assistant[/dim]\n"
            f"  [dim]/help · /new · /clear · /quit[/dim]\n"
        )

    def _status_text(self) -> str:
        config = load_config()
        ai = config.get("ai", {})
        provider = ai.get("provider", "openai")
        model = ai.get("model", "gpt-4o-mini")
        registry = PROVIDER_REGISTRY.get(provider, {})
        name = registry.get("name", provider)
        return f"[dot]●[/dot] {name.lower()} · {model}"

    def _update_status(self):
        self.query_one("#status-bar", Static).update(self._status_text())

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        if text.startswith("/"):
            self._handle_command(text)
            return
        self._handle_input(text)

    def _handle_command(self, cmd: str):
        chat = self.query_one("#chat-container", RichLog)
        inp = self.query_one("#chat-input", Input)
        inp.value = ""
        if cmd in ("/help", "/?"):
            chat.write(f"  [{DIM}]/help   show commands[/]")
            chat.write(f"  [{DIM}]/new    new session[/]")
            chat.write(f"  [{DIM}]/clear  clear screen[/]")
            chat.write(f"  [{DIM}]/quit   exit[/]")
        elif cmd == "/new":
            self.action_new_session()
        elif cmd == "/clear":
            self.action_clear()
        elif cmd in ("/quit", "/exit"):
            self.exit()
        else:
            chat.write(f"  [{ACCENT}]unknown command: {cmd}[/]")

    @work(exclusive=True)
    async def _handle_input(self, text: str):
        chat = self.query_one("#chat-container", RichLog)
        inp = self.query_one("#chat-input", Input)
        inp.value = ""
        inp.disabled = True

        self.session.add_message("user", text)
        chat.write("")
        chat.write(f"[bold {ACCENT}]›[/bold {ACCENT}] [{TEXT}]{text}[/{TEXT}]")
        chat.write("")

        config = load_config()
        provider_config = get_provider_config(config)
        provider = create_provider(provider_config)

        messages = self.session.messages.copy()
        if not any(m["role"] == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": SYSTEM_PROMPTS["default"]})

        chat.write(f"[{DIM}]⏺ [/] ", end="")
        full = ""
        try:
            async for chunk in provider.chat_stream(messages):
                full += chunk
                chat.write(f"[{TEXT}]{chunk}[/{TEXT}]", end="")
        except Exception as e:
            chat.write(f"[{ACCENT}]error: {e}[/]")

        chat.write("")
        if full:
            self.session.add_message("assistant", full)
            save_session(self.session)

        inp.disabled = False
        inp.focus()

    def action_new_session(self):
        self.session = Session()
        chat = self.query_one("#chat-container", RichLog)
        chat.clear()
        chat.write(self._welcome_text(chat.min_width))

    def action_clear(self):
        chat = self.query_one("#chat-container", RichLog)
        chat.clear()
        chat.write(self._welcome_text(chat.min_width))
