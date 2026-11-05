## Python Resource Stress Testing Script to generate controlled CPU and RAM utilization on your EC2, Azure VM, or GCP Compute Engine instance.

### The script will allow you to specify:**
- **CPU utilization:** Target percentage (e.g., 30%, 60%, 80%).
- **RAM utilization: Target percentage (e.g., 40%, 70%, 85%).
- **Duration: 5 minutes, 10 minutes, 15 minutes, etc.
- **Live monitoring:** CPU and RAM usage while the script runs.
- **Automatic cleanup:** Stops consuming resources when the duration expires and releases allocated memory.
It uses Python multiprocessing for CPU load and controlled memory allocation for RAM load. It doesn't require cloud-specific SDKs, so the same script works across AWS, Azure and GCP.
1. Python script – resource_stress.py
```
#!/usr/bin/env python3

"""
Resource Stress Testing Tool
CPU + RAM utilization generator for AWS, Azure and GCP.

Usage:
    python resource_stress.py --cpu 70 --memory 60 --duration 5m
"""

import argparse
import multiprocessing as mp
import os
import time
import sys

try:
    import psutil
except ImportError:
    print("Missing dependency. Install using: pip install psutil")
    sys.exit(1)


# CPU worker: maintain requested CPU utilization using duty cycling.
def cpu_worker(target_cpu, stop_event):
    period = 0.2
    busy_time = period * target_cpu / 100

    while not stop_event.is_set():
        cycle_start = time.monotonic()
        busy_until = cycle_start + busy_time

        while time.monotonic() < busy_until:
            if stop_event.is_set():
                return
            _ = 12345 * 67890

        remaining = period - (time.monotonic() - cycle_start)

        if remaining > 0:
            stop_event.wait(remaining)


def parse_duration(value):
    """Accept 300, 5m, 1h or 30s."""
    value = value.strip().lower()

    try:
        if value.endswith("h"):
            return int(float(value[:-1]) * 3600)
        if value.endswith("m"):
            return int(float(value[:-1]) * 60)
        if value.endswith("s"):
            return int(float(value[:-1]))
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Duration must be seconds or use s, m, h (e.g. 300, 5m, 1h)"
        )


def allocate_memory(target_percent, reserve_gb):
    """Allocate and touch memory without consuming the OS safety reserve."""

    memory = psutil.virtual_memory()

    target_bytes = int(memory.total * target_percent / 100)
    currently_used = memory.total - memory.available

    required = max(0, target_bytes - currently_used)

    reserve_bytes = int(reserve_gb * 1024**3)
    safe_available = max(0, memory.available - reserve_bytes)

    allocation_size = min(required, safe_available)

    if allocation_size < required:
        print(
            f"\nWARNING: Requested RAM target cannot safely be reached. "
            f"Allocating {allocation_size / 1024**3:.2f} GB "
            f"instead of {required / 1024**3:.2f} GB."
        )

    print(f"Current RAM usage : {memory.percent:.1f}%")
    print(f"Requested RAM     : {target_percent:.1f}%")
    print(f"Allocating        : {allocation_size / 1024**3:.2f} GB")

    allocated = []

    try:
        chunk_size = 1024 * 1024  # 1 MB

        for offset in range(0, allocation_size, chunk_size):
            size = min(chunk_size, allocation_size - offset)

            block = bytearray(size)

            # Touch each page to ensure physical memory is committed.
            for page in range(0, size, 4096):
                block[page] = 1

            allocated.append(block)

    except (MemoryError, OSError) as error:
        print(f"\nMemory allocation stopped: {error}")

    return allocated


def run_stress(args):
    cpu_count = os.cpu_count() or 1

    print("\n========================================")
    print("       RESOURCE STRESS TEST")
    print("========================================")
    print(f"CPU cores       : {cpu_count}")
    print(f"Target CPU      : {args.cpu}%")
    print(f"Target RAM      : {args.memory}%")
    print(f"Duration        : {args.duration} seconds")
    print("========================================\n")

    stop_event = mp.Event()
    processes = []
    allocated_memory = []

    try:
        # Start CPU workers.
        if args.cpu > 0:
            for _ in range(cpu_count):
                process = mp.Process(
                    target=cpu_worker,
                    args=(args.cpu, stop_event)
                )
                process.start()
                processes.append(process)

        # Allocate RAM.
        if args.memory > 0:
            allocated_memory = allocate_memory(
                args.memory,
                args.reserve_gb
            )

        print("\nStress test running...\n")

        start_time = time.monotonic()

        # Live resource monitoring.
        while time.monotonic() - start_time < args.duration:
            elapsed = time.monotonic() - start_time
            remaining = max(0, args.duration - elapsed)

            cpu_usage = psutil.cpu_percent(interval=1)
            ram_usage = psutil.virtual_memory().percent
            ram_used = psutil.virtual_memory().used / 1024**3

            print(
                f"\rElapsed: {elapsed:6.0f}s | "
                f"Remaining: {remaining:6.0f}s | "
                f"CPU: {cpu_usage:5.1f}% | "
                f"RAM: {ram_usage:5.1f}% | "
                f"RAM Used: {ram_used:.2f} GB",
                end="",
                flush=True
            )

        print("\n\nStress duration completed.")

    except KeyboardInterrupt:
        print("\n\nStress test interrupted by user.")

    finally:
        print("\nCleaning up resources...")

        stop_event.set()

        for process in processes:
            process.join(timeout=3)

            if process.is_alive():
                process.terminate()
                process.join()

        # Release allocated RAM.
        allocated_memory.clear()

        print("CPU workers stopped.")
        print("Allocated RAM released.")
        print("Stress test completed.")

        stop_event.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="CPU and RAM stress testing utility"
    )

    parser.add_argument(
        "--cpu",
        type=float,
        default=0,
        help="Target CPU percentage (0-100)"
    )

    parser.add_argument(
        "--memory",
        type=float,
        default=0,
        help="Target total RAM utilization percentage (0-100)"
    )

    parser.add_argument(
        "--duration",
        type=parse_duration,
        default=300,
        help="Duration: seconds, 5m, 10m, 1h"
    )

    parser.add_argument(
        "--reserve-gb",
        type=float,
        default=1.0,
        help="Keep this much RAM available for the OS (default 1 GB)"
    )

    args = parser.parse_args()

    if not 0 <= args.cpu <= 100:
        parser.error("CPU must be between 0 and 100")

    if not 0 <= args.memory <= 100:
        parser.error("Memory must be between 0 and 100")

    if args.duration <= 0:
        parser.error("Duration must be greater than zero")

    if args.reserve_gb < 0:
        parser.error("Reserve GB cannot be negative")

    run_stress(args)
```



3. Install dependencies
Only one external dependency is required: psutil.
```
Linux / Ubuntu / Amazon Linux
sudo apt update
sudo apt install python3 python3-pip -y
```
```
pip3 install psutil
```

**For Amazon Linux,** if needed:
```
sudo yum install python3 -y
python3 -m pip install psutil
```

**Windows PowerShell**
```
winget install Python.Python.3.12
python -m pip install psutil
```

**RHEL / Rocky Linux**
```
sudo dnf install python3 python3-pip -y
python3 -m pip install psutil
```

3. Script execution methods
You can execute the script with different combinations of CPU, RAM and duration.
Scenario Command
```
50% CPU, 40% RAM, 5 min	python resource_stress.py --cpu 50 --memory 40 --duration 5m
70% CPU, 60% RAM, 10 min	python resource_stress.py --cpu 70 --memory 60 --duration 10m
90% CPU, 80% RAM, 5 min	python resource_stress.py --cpu 90 --memory 80 --duration 5m
CPU only, 5 min	python resource_stress.py --cpu 80 --memory 0 --duration 5m
RAM only, 10 min	python resource_stress.py --cpu 0 --memory 70 --duration 10m
60% CPU, 50% RAM, 300 sec	python resource_stress.py --cpu 60 --memory 50 --duration 300
```
You can also run:
```
python resource_stress.py --help
```

Important: RAM percentage represents total system RAM utilization, not the percentage of RAM allocated by the script. The script preserves a default 1 GB safety reserve, so it may not reach your requested percentage. CPU utilization is an approximate target, not a hard guarantee.
