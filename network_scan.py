import argparse
import concurrent.futures
import ipaddress
import platform
import socket
import subprocess

SYSTEM = platform.system().lower()

COMMON_PORTS = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 135: "msrpc", 139: "netbios", 143: "imap",
    443: "https", 445: "smb", 993: "imaps", 995: "pop3s", 1433: "mssql",
    3306: "mysql", 3389: "rdp", 5432: "postgresql", 5900: "vnc",
    8000: "http-alt", 8080: "http-proxy", 8443: "https-alt",
}


# ---------- Ping sweep ----------

def build_ping_command(ip: str, timeout: int) -> list[str]:
    if SYSTEM == "windows":
        return ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
    if SYSTEM == "darwin":  # macOS: -W is in milliseconds
        return ["ping", "-c", "1", "-W", str(timeout * 1000), ip]
    return ["ping", "-c", "1", "-W", str(timeout), ip]  # Linux


def is_host_alive(ip, timeout: int = 1, debug: bool = False) -> bool:
    try:
        ip = str(ipaddress.ip_address(str(ip)))
    except ValueError:
        return False

    try:
        result = subprocess.run(
            build_ping_command(ip, timeout),
            capture_output=True,
            text=True,
            errors="ignore",
            timeout=timeout + 3,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        if debug:
            print(f"[debug] {ip}: {type(e).__name__}: {e}")
        return False

    out = result.stdout.lower()
    if debug:
        print(f"[debug] {ip}: returncode={result.returncode}\n{result.stdout.strip()}\n")

    if result.returncode != 0:
        return False
    if SYSTEM == "windows":
        return "ttl=" in out  # Windows returns 0 even for "unreachable"
    return True


def local_network() -> str:
    """Guess the local /24 network from the machine's active interface."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packets are sent
        ip = s.getsockname()[0]
    finally:
        s.close()
    return str(ipaddress.ip_network(f"{ip}/24", strict=False))


def get_hosts(network: str) -> list[str]:
    net = ipaddress.ip_network(network, strict=False)
    if net.num_addresses == 1:  # single IP: hosts() would be empty
        return [str(net.network_address)]
    return [str(h) for h in net.hosts()]


def ping_sweep(hosts: list[str], timeout: int, workers: int, debug: bool) -> list[str]:
    alive = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(is_host_alive, h, timeout, debug): h for h in hosts}
        for fut in concurrent.futures.as_completed(futures):
            if fut.result():
                ip = futures[fut]
                alive.append(ip)
                print(f"{ip} is alive", flush=True)
    return sorted(alive, key=ipaddress.ip_address)


# ---------- Port scan ----------

def parse_ports(spec: str) -> list[int]:
    """Accepts 'common', '80', '22,80,443', '1-1024', or a mix."""
    if spec.strip().lower() == "common":
        return sorted(COMMON_PORTS)

    ports = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = (int(x) for x in part.split("-", 1))
            if start > end:
                start, end = end, start
            ports.update(range(start, end + 1))
        else:
            ports.add(int(part))

    if not ports or min(ports) < 1 or max(ports) > 65535:
        raise ValueError("ports must be between 1 and 65535")
    return sorted(ports)


def service_name(port: int) -> str:
    if port in COMMON_PORTS:
        return COMMON_PORTS[port]
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def is_port_open(ip: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def scan_ports(ip: str, ports: list[int], timeout: float, workers: int) -> list[int]:
    open_ports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(is_port_open, ip, p, timeout): p for p in ports}
        for fut in concurrent.futures.as_completed(futures):
            if fut.result():
                open_ports.append(futures[fut])
    return sorted(open_ports)


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Ping sweep + TCP port scanner")
    parser.add_argument("network", nargs="?",
                        help="IP or network, e.g. 192.168.1.0/24 (default: auto-detect)")
    parser.add_argument("-t", "--timeout", type=int, default=1,
                        help="ping timeout in seconds (default 1)")
    parser.add_argument("-w", "--workers", type=int, default=100,
                        help="ping thread count (default 100)")
    parser.add_argument("-d", "--debug", action="store_true", help="print raw ping output")
    parser.add_argument("-p", "--ports",
                        help="ports to scan: 'common', '80', '22,80,443', '1-1024'")
    parser.add_argument("--port-timeout", type=float, default=0.5,
                        help="seconds per port connection (default 0.5)")
    parser.add_argument("--port-workers", type=int, default=200,
                        help="port scan thread count (default 200)")
    parser.add_argument("-Pn", "--no-ping", action="store_true",
                        help="skip the ping sweep and treat all hosts as up")
    args = parser.parse_args()

    network = args.network
    if not network:
        try:
            network = local_network()
        except OSError:
            parser.error("Could not auto-detect network; pass one explicitly.")
        print(f"Auto-detected network: {network}")

    try:
        hosts = get_hosts(network)
        ports = parse_ports(args.ports) if args.ports else []
    except ValueError as e:
        parser.error(str(e))

    if args.no_ping:
        alive = hosts
        print(f"Skipping ping sweep, treating {len(alive)} address(es) as up")
    else:
        alive = ping_sweep(hosts, args.timeout, args.workers, args.debug)
        print(f"\nScanned {len(hosts)} address(es), {len(alive)} host(s) up")

    if ports and alive:
        print(f"\nPort scanning {len(alive)} host(s), {len(ports)} port(s) each...\n")
        for ip in alive:
            open_ports = scan_ports(ip, ports, args.port_timeout, args.port_workers)
            if open_ports:
                print(f"{ip}")
                for p in open_ports:
                    print(f"  {p:>5}/tcp  open  {service_name(p)}")
            else:
                print(f"{ip}: no open ports found")


if __name__ == "__main__":
    main()
