"""Threshold-based alerting."""
from dataclasses import dataclass


@dataclass
class Thresholds:
    cpu: float = 90.0
    mem: float = 90.0
    disk: float = 90.0
    temp: float = 85.0


def check(snap, th: Thresholds):
    """Return a list of human-readable alert strings."""
    alerts = []
    if snap["cpu"]["percent"] >= th.cpu:
        alerts.append(f"CPU usage high: {snap['cpu']['percent']:.0f}% (limit {th.cpu:.0f}%)")
    if snap["memory"]["percent"] >= th.mem:
        alerts.append(f"Memory usage high: {snap['memory']['percent']:.0f}% (limit {th.mem:.0f}%)")
    for d in snap["disks"]:
        if d["percent"] >= th.disk:
            alerts.append(f"Disk {d['mount']} almost full: {d['percent']:.0f}% (limit {th.disk:.0f}%)")
    for name, t in snap["temperatures"].items():
        if t >= th.temp:
            alerts.append(f"Temperature {name}: {t:.0f}°C (limit {th.temp:.0f}°C)")
    return alerts
