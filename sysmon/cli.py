"""Command-line entry point."""
import argparse
import sys
import time

from rich.console import Console
from rich.live import Live

from . import __version__
from .alerts import Thresholds, check
from .collectors import Collector, SORT_KEYS
from .logger import CsvLogger, dump_json
from .ui import Dashboard


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="sysmon", description="Command-line system resource monitor")
    p.add_argument("-i", "--interval", type=float, default=1.0, help="refresh seconds (default 1.0)")
    p.add_argument("-n", "--top", type=int, default=10, help="number of processes to show (default 10)")
    p.add_argument("-s", "--sort", choices=SORT_KEYS.keys(), default="cpu", help="process sort key")
    p.add_argument("-c", "--count", type=int, default=0, help="stop after N refreshes (0 = run forever)")
    p.add_argument("--once", action="store_true", help="print one snapshot of the dashboard and exit")
    p.add_argument("--json", nargs="?", const="-", metavar="FILE", help="dump a JSON snapshot (to FILE or stdout) and exit")
    p.add_argument("--log", metavar="FILE.csv", help="append metrics to a CSV file every refresh")
    p.add_argument("--alert-cpu", type=float, default=90, help="CPU %% alert threshold")
    p.add_argument("--alert-mem", type=float, default=90, help="memory %% alert threshold")
    p.add_argument("--alert-disk", type=float, default=90, help="disk %% alert threshold")
    p.add_argument("--alert-temp", type=float, default=85, help="temperature C alert threshold")
    p.add_argument("--bell", action="store_true", help="ring the terminal bell on new alerts")
    p.add_argument("-v", "--version", action="version", version=f"sysmon {__version__}")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    console = Console()
    collector = Collector()
    info = collector.system_info()
    th = Thresholds(args.alert_cpu, args.alert_mem, args.alert_disk, args.alert_temp)
    time.sleep(0.5)  # let CPU counters accumulate a sample

    if args.json is not None:
        snap = collector.snapshot(args.top, args.sort)
        out = dump_json(snap, info, None if args.json == "-" else args.json)
        if args.json == "-":
            print(out)
        else:
            console.print(f"[green]Snapshot written to {args.json}")
        return 0

    dash = Dashboard(info)
    logger = CsvLogger(args.log) if args.log else None
    seen_alerts = set()

    def step():
        snap = collector.snapshot(args.top, args.sort)
        alerts = check(snap, th)
        if logger:
            logger.write(snap, alerts)
        new = set(alerts) - seen_alerts
        if args.bell and new:
            sys.stdout.write("\a")
        seen_alerts.clear()
        seen_alerts.update(alerts)
        return dash.render(snap, alerts, args.sort)

    try:
        if args.once:
            console.print(step())
            return 0
        n = 0
        with Live(step(), console=console, screen=True, auto_refresh=False) as live:
            while True:
                time.sleep(args.interval)
                live.update(step(), refresh=True)
                n += 1
                if args.count and n >= args.count:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if logger:
            logger.close()
    console.print("[bold cyan]sysmon stopped. Bye![/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
