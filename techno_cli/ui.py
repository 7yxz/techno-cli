import shutil
import subprocess
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt  # noqa: F401  (re-exported)
from rich.table import Table
from rich.text import Text

from . import __version__

console = Console()
ACCENT = "magenta"


def banner(sync=None):
    t = Text()
    t.append("techno", style="bold magenta")
    t.append("-cli", style="bold cyan")
    t.append(f"  v{__version__}\n", style="dim")
    t.append("watch anime from your terminal", style="italic dim")
    t.append("\nsync: ", style="dim")
    t.append(", ".join(sync) if sync else "off (techno-cli --login anilist|mal|kitsu)",
             style="green" if sync else "dim")
    console.print(Panel.fit(t, border_style=ACCENT, box=box.ROUNDED, padding=(0, 3)))


def warn(msg):
    console.print(f"[yellow]![/] {msg}")


def error(msg):
    console.print(f"[bold red]error:[/] {msg}")


def now_playing(title, label, provider, quality, dub):
    body = Text()
    body.append(title + "\n", style="bold")
    body.append(label, style="cyan")
    body.append(f"   {provider}  |  {quality}p  |  {'dub' if dub else 'sub'}", style="dim")
    console.print(Panel(body, title="now playing", title_align="left",
                        border_style=ACCENT, box=box.ROUNDED))


def controls():
    return Prompt.ask("[cyan]n[/]ext  [cyan]p[/]rev  [cyan]r[/]eplay  [cyan]s[/]elect  [cyan]q[/]uit",
                      choices=["n", "p", "r", "s", "q"], default="n", show_choices=False)


def pick(items, label):
    """items: list of (text, value). Returns the chosen value."""
    if not items:
        error("nothing found")
        sys.exit(1)
    if shutil.which("fzf"):
        lines = [f"{i}\t{t}" for i, (t, _) in enumerate(items)]
        p = subprocess.run(
            ["fzf", "--with-nth=2..", "--delimiter=\t", "--reverse", "--border=rounded",
             "--height=70%", "--cycle", "--prompt", label + " > ",
             "--color=hl:magenta,hl+:magenta,pointer:cyan,prompt:cyan,border:magenta"],
            input="\n".join(lines), text=True, stdout=subprocess.PIPE)
        if not p.stdout.strip():
            sys.exit(0)
        return items[int(p.stdout.split("\t")[0])][1]
    table = Table(box=box.SIMPLE_HEAD, border_style=ACCENT, header_style="bold cyan")
    table.add_column("#", justify="right", style="dim")
    table.add_column(label)
    for i, (t, _) in enumerate(items, 1):
        table.add_row(str(i), t)
    console.print(table)
    while True:
        n = Prompt.ask(f"[cyan]{label}[/] #")
        if n.strip().isdigit() and 1 <= int(n) <= len(items):
            return items[int(n) - 1][1]
