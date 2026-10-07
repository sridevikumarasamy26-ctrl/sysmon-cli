"""CSV session logging and JSON export."""
import csv
import json
import os


class CsvLogger:
    FIELDS = ["timestamp", "cpu_percent", "mem_percent", "swap_percent",
              "net_up_Bps", "net_down_Bps", "disk_read_Bps", "disk_write_Bps",
              "process_count", "alerts"]

    def __init__(self, path):
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self._f = open(path, "a", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        if new:
            self._w.writerow(self.FIELDS)

    def write(self, snap, alerts):
        self._w.writerow([
            snap["timestamp"], snap["cpu"]["percent"], snap["memory"]["percent"],
            snap["swap"]["percent"], round(snap["network"]["up"]), round(snap["network"]["down"]),
            round(snap["disk_io"]["read"]), round(snap["disk_io"]["write"]),
            snap["process_count"], " | ".join(alerts),
        ])
        self._f.flush()

    def close(self):
        self._f.close()


def dump_json(snap, info, path=None):
    data = json.dumps({"system": info, "snapshot": snap}, indent=2, default=str)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
    return data
