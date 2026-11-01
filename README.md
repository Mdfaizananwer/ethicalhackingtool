# Network_scan.py

A small, dependency-free Python tool that does two things:

1. **Ping sweep**: finds which hosts on a network respond to ICMP echo.
2. **TCP port scan**: checks which ports are open on the hosts it found.

It works on Windows, Linux, and macOS using only the Python standard library.

> **Legal notice:** Only scan networks and systems you own or have explicit written permission to test. Unauthorized scanning may violate laws, workplace policies, and your ISP's terms of service.

## Features

- Cross-platform ping handling (Windows, Linux, macOS timeout differences are handled)
- Windows false-positive fix: replies like "Destination host unreachable" are not counted as alive
- Auto-detects your local /24 network when no target is given
- Works with a single IP, a CIDR range, or a mix of both styles
- Multithreaded ping sweep and port scan
- Flexible port selection: `common`, single ports, lists, and ranges
- Service names shown for open ports
- `-Pn` option to skip ping for hosts that block ICMP
- Debug mode that prints raw `ping` output
- Input validation, so malformed addresses are never passed to the system `ping` command

## Requirements

- Python 3.9 or newer
- The `ping` command available on your system (included by default on Windows, macOS, and most Linux distributions)

No `pip install` needed.

## Installation

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

Or just download `scan.py`.

## Usage

```text
python scan.py [network] [options]
```

| Option | Description | Default |
| --- | --- | --- |
| `network` | IP or CIDR range, e.g. `192.168.1.0/24`. Optional: auto-detects if omitted | auto |
| `-t`, `--timeout` | Ping timeout in seconds | `1` |
| `-w`, `--workers` | Threads for the ping sweep | `100` |
| `-d`, `--debug` | Print raw ping output for each host | off |
| `-p`, `--ports` | Ports to scan: `common`, `80`, `22,80,443`, `1-1024` | none |
| `--port-timeout` | Seconds to wait per port connection | `0.5` |
| `--port-workers` | Threads for the port scan | `200` |
| `-Pn`, `--no-ping` | Skip the ping sweep and treat all hosts as up | off |

### Examples

Ping sweep your auto-detected local network:

```bash
python scan.py
```

Ping sweep a specific network:

```bash
python scan.py 192.168.0.0/24
```

Sweep, then scan common ports on every live host:

```bash
python scan.py 192.168.0.0/24 -p common
```

Scan ports 1-1024 on a single host:

```bash
python scan.py 192.168.0.1 -p 1-1024
```

Scan a host that blocks ping:

```bash
python scan.py 192.168.0.105 -p 22,80,443 -Pn
```

Debug a host that should be up but isn't being detected:

```bash
python scan.py 192.168.0.1 -d
```

### Example output

```text
Auto-detected network: 192.168.0.0/24
192.168.0.1 is alive
192.168.0.105 is alive

Scanned 254 address(es), 2 host(s) up

Port scanning 2 host(s), 22 port(s) each...

192.168.0.1
     53/tcp  open  dns
     80/tcp  open  http
    443/tcp  open  https
192.168.0.105: no open ports found
```

## Common ports scanned with `-p common`

`21` ftp, `22` ssh, `23` telnet, `25` smtp, `53` dns, `80` http, `110` pop3, `135` msrpc, `139` netbios, `143` imap, `443` https, `445` smb, `993` imaps, `995` pop3s, `1433` mssql, `3306` mysql, `3389` rdp, `5432` postgresql, `5900` vnc, `8000` http-alt, `8080` http-proxy, `8443` https-alt

## Troubleshooting

**"0 host(s) up" on a network scan**

- Your network may not be `192.168.1.0/24`. Run `ipconfig` (Windows) or `ip a` / `ifconfig` (Linux/macOS), find your IPv4 address, and scan that range. Or just run `python scan.py` with no arguments to auto-detect.
- Some Wi-Fi networks use client isolation, which blocks devices from reaching each other.
- Windows Firewall blocks incoming ping by default, so many Windows PCs will appear down even when they are on. Use `-Pn` with a port scan to check them.

**Scanning a single IP shows 0 hosts**

Use the latest version of the script, which handles single addresses correctly. For hosts that block ping, add `-Pn`.

**Public IPs show as down**

Most public IPs and home routers do not answer ping from the internet.

**Port scan is slow**

Ports silently dropped by a firewall make each connection attempt wait for the full timeout. Lower `--port-timeout` or raise `--port-workers`, at the cost of possibly missing slow responders.

## Limitations

- TCP connect scan only (no UDP, no SYN/stealth scanning)
- IPv4 networks are the focus; auto-detection uses IPv4
- "Closed" and "filtered" ports are both reported as not open
- ICMP-based discovery misses hosts that block ping (use `-Pn`)
- Very large ranges (such as a `/16`) will take a long time

## How it works

- **Ping sweep:** runs the system `ping` command once per address in a thread pool, with the right flags and timeout units for each OS.
- **Port scan:** opens a TCP connection with `socket.create_connection` to each port. A completed connection means the port is open.

## Contributing

Issues and pull requests are welcome. Ideas: UDP scanning, banner grabbing, JSON/CSV output, IPv6 support.

## License

Released under the MIT License. Add a `LICENSE` file to your repository to match.

## Disclaimer

This tool is provided for educational and authorized administrative use. The author is not responsible for misuse or any damage caused by it.
