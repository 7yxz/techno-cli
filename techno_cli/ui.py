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


CONTROLS = "[cyan]n[/]ext  [cyan]p[/]rev  [cyan]r[/]eplay  re[cyan]f[/]resh  [cyan]s[/]elect  [cyan]c[/]onfig  [cyan]q[/]uit"


def controls():
    return Prompt.ask(CONTROLS, choices=["n", "p", "r", "f", "s", "c", "q"], default="n", show_choices=False)


def watch_page(info, title, label, idx, total, status, synopsis=True):
    """Full-screen info page shown after an episode. Returns the chosen control key."""
    from rich.progress_bar import ProgressBar
    info = info or {}
    with console.screen():
        console.clear()
        head = Text()
        head.append(info.get("title") or title, style="bold magenta")
        if info.get("romaji") and info["romaji"] != info.get("title"):
            head.append(f"\n{info['romaji']}", style="dim")
        bits = [str(x) for x in (info.get("format"), info.get("year"), info.get("status"), info.get("studio")) if x]
        if info.get("score"):
            bits.append(f"{info['score'] / 10:.1f}/10")
        if bits:
            head.append("\n" + "  |  ".join(bits), style="cyan")
        if info.get("genres"):
            head.append("\n" + ", ".join(info["genres"]), style="dim")
        console.print(Panel(head, border_style=ACCENT, box=box.ROUNDED, title="watching", title_align="left"))
        if synopsis and info.get("synopsis"):
            console.print(Panel(info["synopsis"], border_style="dim", box=box.ROUNDED, title="synopsis",
                                title_align="left"))
        console.print(f"\n[bold]{label}[/]  [dim]{idx + 1} of {total}[/]")
        console.print(ProgressBar(total=total, completed=idx + 1, width=min(60, console.width - 4)))
        console.print(f"\n[dim]{status}[/]\n")
        return controls()


def _pager(items, label):
    """Full-screen picker used when fzf is missing: filter by typing, number to select."""
    page, q = 0, ""
    with console.screen():
        while True:
            view = [(i, t) for i, (t, _) in enumerate(items, 1) if q.lower() in t.lower()]
            size = max(5, console.size.height - 9)
            pages = max(1, -(-len(view) // size))
            page = min(page, pages - 1)
            console.clear()
            console.print(Panel(f"[bold]{label}[/]   filter: [cyan]{q or '-'}[/]   page {page + 1}/{pages}",
                                border_style=ACCENT, box=box.ROUNDED))
            table = Table(box=box.SIMPLE_HEAD, border_style=ACCENT, header_style="bold cyan")
            table.add_column("#", justify="right", style="dim")
            table.add_column(label)
            for i, t in view[page * size:(page + 1) * size]:
                table.add_row(str(i), t)
            console.print(table)
            console.print("[dim]number: select  |  text: filter  |  enter: clear filter  |  n/p: page  |  q: cancel[/]")
            cmd = Prompt.ask(">").strip()
            if cmd.isdigit() and any(i == int(cmd) for i, _ in view):
                return items[int(cmd) - 1][1]
            if cmd == "n":
                page += 1
            elif cmd == "p":
                page = max(0, page - 1)
            elif cmd == "q":
                sys.exit(0)
            else:
                q, page = cmd, 0


def pick(items, label):
    """items: list of (text, value). Opens a full-screen picker and returns the chosen value."""
    if not items:
        error("nothing found")
        sys.exit(1)
    if shutil.which("fzf"):
        lines = [f"{i}\t{t}" for i, (t, _) in enumerate(items)]
        p = subprocess.run(
            ["fzf", "--with-nth=2..", "--delimiter=\t", "--layout=reverse", "--border=rounded",
             "--cycle", "--info=inline", f"--prompt={label} > ",
             f"--header={label}   enter: select   esc: cancel   type to filter",
             "--preview=echo {2..}", "--preview-window=down:3:wrap:border-rounded",
             "--color=hl:magenta,hl+:magenta,pointer:cyan,prompt:cyan,border:magenta,header:dim"],
            input="\n".join(lines), text=True, stdout=subprocess.PIPE)
        if not p.stdout.strip():
            sys.exit(0)
        return items[int(p.stdout.split("\t")[0])][1]
    return _pager(items, label)
