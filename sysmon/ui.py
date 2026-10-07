"""Rich-based terminal dashboard."""
from collections import deque

from rich import box
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

SPARKS = "▁▂▃▄▅▆▇█"


def human(n, suffix="B"):
    n = float(n)
    for unit in ["", "K", "M", "G", "T"]:
        if abs(n) < 1024:
            return f"{n:6.1f} {unit}{suffix}"
        n /= 1024
    return f"{n:.1f} P{suffix}"


def color_for(pct):
    return "green" if pct < 60 else "yellow" if pct < 85 else "red"


def bar(pct, width=24):
    filled = int(round(width * min(pct, 100) / 100))
    c = color_for(pct)
    t = Text()
    t.append("█" * filled, style=c)
    t.append("░" * (width - filled), style="grey37")
    t.append(f" {pct:5.1f}%", style=f"bold {c}")
    return t


def spark(values, width=30):
    vals = list(values)[-width:]
    t = Text()
    for v in vals:
        idx = min(int(v / 100 * (len(SPARKS) - 1)), len(SPARKS) - 1)
        t.append(SPARKS[max(idx, 0)], style=color_for(v))
    return t


class Dashboard:
    def __init__(self, info, history_len=60):
        self.info = info
        self.cpu_hist = deque(maxlen=history_len)
        self.mem_hist = deque(maxlen=history_len)
        self.up_hist = deque(maxlen=history_len)
        self.down_hist = deque(maxlen=history_len)

    def _header(self, snap, alerts):
        i = self.info
        t = Text()
        t.append(f" {i['host']} ", style="bold white on blue")
        t.append(f"  {i['os']} ({i['arch']})  ", style="cyan")
        t.append(f"uptime {i['uptime']}  ", style="green")
        t.append(f"cores {i['cores_physical']}P/{i['cores_logical']}L  ", style="magenta")
        t.append(f"procs {snap['process_count']}  ", style="yellow")
        t.append(snap["timestamp"].replace("T", " "), style="dim")
        return Panel(t, box=box.ROUNDED, style="red" if alerts else "blue")

    def _cpu(self, snap):
        cpu = snap["cpu"]
        rows = [Text.assemble("Total  ", bar(cpu["percent"], 24)),
                Text.assemble("Trend  ", spark(self.cpu_hist))]
        meta = []
        if cpu["freq_mhz"]:
            meta.append(f"freq {cpu['freq_mhz']:.0f} MHz")
        if cpu["load_avg"]:
            meta.append("load " + " ".join(f"{x:.2f}" for x in cpu["load_avg"]))
        if meta:
            rows.append(Text("  ".join(meta), style="dim"))
        cores = [Text.assemble(f"C{i:<2} ", bar(p, 10)) for i, p in enumerate(cpu["per_core"])]
        rows.append(Columns(cores, equal=True, expand=True))
        return Panel(Group(*rows), title="[bold]CPU", border_style="cyan", box=box.ROUNDED)

    def _memory(self, snap):
        m, s = snap["memory"], snap["swap"]
        rows = [
            Text.assemble("RAM    ", bar(m["percent"], 20)),
            Text(f"       {human(m['used'])} / {human(m['total'])}  (avail {human(m['available'])})", style="dim"),
            Text.assemble("Swap   ", bar(s["percent"], 20)),
            Text(f"       {human(s['used'])} / {human(s['total'])}", style="dim"),
            Text.assemble("Trend  ", spark(self.mem_hist)),
        ]
        return Panel(Group(*rows), title="[bold]Memory", border_style="magenta", box=box.ROUNDED)

    def _disks(self, snap):
        tbl = Table(box=box.SIMPLE_HEAD, expand=True)
        tbl.add_column("Mount", overflow="ellipsis", max_width=22)
        tbl.add_column("FS")
        tbl.add_column("Used / Total", justify="right")
        tbl.add_column("Usage")
        for d in snap["disks"][:8]:
            tbl.add_row(d["mount"], d["fs"], f"{human(d['used'])} / {human(d['total'])}", bar(d["percent"], 14))
        io = snap["disk_io"]
        foot = Text(f"I/O  read {human(io['read'])}/s   write {human(io['write'])}/s", style="dim")
        return Panel(Group(tbl, foot), title="[bold]Disks", border_style="yellow", box=box.ROUNDED)

    def _network(self, snap):
        n = snap["network"]
        rows = [
            Text.assemble(("▲ Up    ", "bold green"), f"{human(n['up'])}/s   total {human(n['total_sent'])}"),
            Text.assemble(("▼ Down  ", "bold cyan"), f"{human(n['down'])}/s   total {human(n['total_recv'])}"),
        ]
        extra = []
        for name, t in list(snap["temperatures"].items())[:3]:
            extra.append(f"{name}: {t:.0f}°C")
        b = snap["battery"]
        if b:
            extra.append(f"battery {b['percent']:.0f}% {'(charging)' if b['plugged'] else '(on battery)'}")
        if extra:
            rows.append(Text("  ".join(extra), style="dim"))
        return Panel(Group(*rows), title="[bold]Network / Sensors", border_style="green", box=box.ROUNDED)

    def _procs(self, snap, sort_by):
        tbl = Table(box=box.SIMPLE_HEAD, expand=True)
        tbl.add_column("PID", justify="right")
        tbl.add_column("Name", overflow="ellipsis", max_width=28)
        tbl.add_column("User", overflow="ellipsis", max_width=14)
        tbl.add_column("CPU%", justify="right")
        tbl.add_column("MEM%", justify="right")
        tbl.add_column("Status")
        for p in snap["processes"]:
            tbl.add_row(str(p["pid"]), p["name"], str(p.get("username") or "-"),
                        f"[{color_for(p['cpu_percent'])}]{p['cpu_percent']:.1f}[/]",
                        f"[{color_for(p['memory_percent'])}]{p['memory_percent']:.1f}[/]",
                        p["status"])
        return Panel(tbl, title=f"[bold]Top Processes (sorted by {sort_by})", border_style="blue", box=box.ROUNDED)

    def _alerts(self, alerts):
        if not alerts:
            return Panel(Text("✔ All systems normal", style="green"), title="Alerts", border_style="green", box=box.ROUNDED)
        return Panel(Group(*[Text("⚠ " + a, style="bold red") for a in alerts]),
                     title="[bold red]Alerts", border_style="red", box=box.ROUNDED)

    def render(self, snap, alerts, sort_by="cpu"):
        self.cpu_hist.append(snap["cpu"]["percent"])
        self.mem_hist.append(snap["memory"]["percent"])
        top = Table.grid(expand=True)
        top.add_column(ratio=3)
        top.add_column(ratio=2)
        top.add_row(self._cpu(snap), self._memory(snap))
        mid = Table.grid(expand=True)
        mid.add_column(ratio=3)
        mid.add_column(ratio=2)
        mid.add_row(self._disks(snap), self._network(snap))
        return Group(self._header(snap, alerts), top, mid,
                     self._procs(snap, sort_by), self._alerts(alerts))
