import subprocess

def kill_port(port):
    print(f"Scanning for process on port {port}...")
    try:
        # Run netstat to find the PID listening on the port
        cmd = f'netstat -aon | findstr :{port}'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0 or not result.stdout:
            print(f"No process found on port {port}")
            return

        pids = set()
        for line in result.stdout.splitlines():
            if "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    pids.add(pid)
        
        for pid in pids:
            if pid == "0": continue
            print(f"Killing PID {pid} on port {port}")
            subprocess.run(f'taskkill /F /PID {pid}', shell=True)
            
    except Exception as e:
        print(f"Error handling port {port}: {e}")

if __name__ == "__main__":
    # Backend
    # Frontend common ports
    PORTS = [5000] + list(range(5173, 5186)) + [5300, 5301]
    for p in PORTS:
        kill_port(p)
