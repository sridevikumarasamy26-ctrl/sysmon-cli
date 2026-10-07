# sysmon – Command-Line System Resource Monitor

A live terminal dashboard (like `htop` + `iostat` + `nload`) written in Python.

## Features
- Live CPU (total, per-core, frequency, load average), RAM, swap
- Disk usage per mount + disk read/write speed
- Network upload/download speed and totals
- Top-N processes, sortable by cpu / mem / pid / name
- Sparkline history graphs for CPU and memory
- Temperature and battery (when the OS exposes them)

## Add-ons
- Threshold alerts (CPU, memory, disk, temperature) with optional terminal bell
- CSV logging of every refresh (`--log`)
- JSON snapshot export (`--json`)
- One-shot mode (`--once`) and fixed-length runs (`-c N`)

## Install
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt

## Run
    python -m sysmon                       # live dashboard, Ctrl+C to quit
    python -m sysmon -i 2 -n 15 -s mem     # refresh 2s, 15 procs, sort by memory
    python -m sysmon --log session.csv     # log to CSV while monitoring
    python -m sysmon --alert-cpu 70 --alert-mem 80 --bell
    python -m sysmon --once                # print one dashboard frame
    python -m sysmon --json                # JSON to stdout
    python -m sysmon --json report.json    # JSON to file
    python -m sysmon -h                    # all options
