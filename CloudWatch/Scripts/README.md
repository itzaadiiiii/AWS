Python Resource Stress Testing Script to generate controlled CPU and RAM utilization on your EC2, Azure VM, or GCP Compute Engine instance.

The script will allow you to specify:
- CPU utilization: Target percentage (e.g., 30%, 60%, 80%).
- RAM utilization: Target percentage (e.g., 40%, 70%, 85%).
- Duration: 5 minutes, 10 minutes, 15 minutes, etc.
- Live monitoring: CPU and RAM usage while the script runs.
- Automatic cleanup: Stops consuming resources when the duration expires and releases allocated memory.
It uses Python multiprocessing for CPU load and controlled memory allocation for RAM load. It doesn't require cloud-specific SDKs, so the same script works across AWS, Azure and GCP.
1. Python script – resource_stress.py
#!/usr/bin/env python3        allocated_memory.clear()        print("CPU workers stopped.")        print("Allocated RAM released.")        print("Stress test completed.")        stop_event.close()if __name__ == "__main__":    parser = argparse.ArgumentParser(        description="CPU and RAM stress testing utility"    )    parser.add_argument(        "--cpu",        type=float,        default=0,        help="Target CPU percentage (0-100)"    )    parser.add_argument(        "--memory",        type=float,        default=0,        help="Target total RAM utilization percentage (0-100)"    )    parser.add_argument(        "--duration",        type=parse_duration,        default=300,        help="Duration: seconds, 5m, 10m, 1h"    )    parser.add_argument(        "--reserve-gb",        type=float,        default=1.0,        help="Keep this much RAM available for the OS (default 1 GB)"    )    args = parser.parse_args()    if not 0 <= args.cpu <= 100:        parser.error("CPU must be between 0 and 100")    if not 0 <= args.memory <= 100:        parser.error("Memory must be between 0 and 100")    if args.duration <= 0:        parser.error("Duration must be greater than zero")    if args.reserve_gb < 0:        parser.error("Reserve GB cannot be negative")    run_stress(args)



2. Install dependencies
Only one external dependency is required: psutil.

Linux / Ubuntu / Amazon Linux
sudo apt update
sudo apt install python3 python3-pip -y

pip3 install psutil


For Amazon Linux, if needed:
sudo yum install python3 -y
python3 -m pip install psutil


Windows PowerShell
winget install Python.Python.3.12
python -m pip install psutil


RHEL / Rocky Linux
sudo dnf install python3 python3-pip -y
python3 -m pip install psutil


3. Script execution methods
You can execute the script with different combinations of CPU, RAM and duration.
Scenario	Command
50% CPU, 40% RAM, 5 min	python resource_stress.py --cpu 50 --memory 40 --duration 5m
70% CPU, 60% RAM, 10 min	python resource_stress.py --cpu 70 --memory 60 --duration 10m
90% CPU, 80% RAM, 5 min	python resource_stress.py --cpu 90 --memory 80 --duration 5m
CPU only, 5 min	python resource_stress.py --cpu 80 --memory 0 --duration 5m
RAM only, 10 min	python resource_stress.py --cpu 0 --memory 70 --duration 10m
60% CPU, 50% RAM, 300 sec	python resource_stress.py --cpu 60 --memory 50 --duration 300

You can also run:
python resource_stress.py --help


Important: RAM percentage represents total system RAM utilization, not the percentage of RAM allocated by the script. The script preserves a default 1 GB safety reserve, so it may not reach your requested percentage. CPU utilization is an approximate target, not a hard guarantee.
