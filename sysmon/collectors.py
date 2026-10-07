"""Collects system metrics via psutil."""
import platform
import socket
import time
from datetime import datetime, timedelta

import psutil

SORT_KEYS = {"cpu": "cpu_percent", "mem": "memory_percent", "pid": "pid", "name": "name"}


class Collector:
    def __init__(self):
        self._last_time = time.time()
        self._last_net = psutil.net_io_counters()
        self._last_disk = psutil.disk_io_counters()
        psutil.cpu_percent(percpu=True)  # prime counters
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    @staticmethod
    def system_info():
        boot = datetime.fromtimestamp(psutil.boot_time())
        return {
            "host": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "python": platform.python_version(),
            "boot_time": boot.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": str(timedelta(seconds=int(time.time() - psutil.boot_time()))),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
        }

    def _processes(self, top_n, sort_by):
        procs = []
        attrs = ["pid", "name", "username", "cpu_percent", "memory_percent", "status"]
        for p in psutil.process_iter(attrs):
            info = p.info
            if info.get("name") is None:
                continue
            info["cpu_percent"] = info.get("cpu_percent") or 0.0
            info["memory_percent"] = info.get("memory_percent") or 0.0
            procs.append(info)
        key = SORT_KEYS.get(sort_by, "cpu_percent")
        rev = key not in ("name", "pid")
        procs.sort(key=lambda x: x[key], reverse=rev)
        return procs[:top_n], len(procs)

    def snapshot(self, top_n=10, sort_by="cpu"):
        now = time.time()
        dt = max(now - self._last_time, 1e-6)

        net = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()
        net_rate = {
            "up": (net.bytes_sent - self._last_net.bytes_sent) / dt,
            "down": (net.bytes_recv - self._last_net.bytes_recv) / dt,
        }
        disk_rate = {"read": 0.0, "write": 0.0}
        if disk_io and self._last_disk:
            disk_rate["read"] = (disk_io.read_bytes - self._last_disk.read_bytes) / dt
            disk_rate["write"] = (disk_io.write_bytes - self._last_disk.write_bytes) / dt
        self._last_time, self._last_net, self._last_disk = now, net, disk_io

        vm, sw = psutil.virtual_memory(), psutil.swap_memory()
        freq = psutil.cpu_freq()
        try:
            load = psutil.getloadavg()
        except (AttributeError, OSError):
            load = None

        partitions = []
        skip_fs = {"squashfs", "iso9660", "overlay", "tmpfs", "devtmpfs", "fuse.rclone", "autofs"}
        for part in psutil.disk_partitions(all=False):
            if part.fstype in skip_fs or "loop" in part.device or part.mountpoint.startswith("/snap"):
                continue
            try:
                u = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            partitions.append({"mount": part.mountpoint, "fs": part.fstype,
                               "total": u.total, "used": u.used, "percent": u.percent})

        temps = {}
        if hasattr(psutil, "sensors_temperatures"):
            try:
                for name, entries in psutil.sensors_temperatures().items():
                    if entries:
                        temps[name] = entries[0].current
            except Exception:
                pass

        battery = None
        if hasattr(psutil, "sensors_battery"):
            try:
                b = psutil.sensors_battery()
                if b:
                    battery = {"percent": b.percent, "plugged": b.power_plugged}
            except Exception:
                pass

        procs, total_procs = self._processes(top_n, sort_by)
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "cpu": {
                "percent": psutil.cpu_percent(),
                "per_core": psutil.cpu_percent(percpu=True),
                "freq_mhz": freq.current if freq else None,
                "load_avg": load,
            },
            "memory": {"total": vm.total, "used": vm.used, "available": vm.available,
                       "percent": vm.percent},
            "swap": {"total": sw.total, "used": sw.used, "percent": sw.percent},
            "disks": partitions,
            "disk_io": disk_rate,
            "network": {**net_rate, "total_sent": net.bytes_sent, "total_recv": net.bytes_recv},
            "temperatures": temps,
            "battery": battery,
            "processes": procs,
            "process_count": total_procs,
        }
