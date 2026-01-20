
import os
import psutil

def kill_port(port):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['name']} (PID {proc.info['pid']}) on port {port}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

if __name__ == "__main__":
    kill_port(5000)
    kill_port(5173)
    kill_port(5174)
    kill_port(5175)
    kill_port(5176)
    kill_port(5177)
