"""Make the Frappe dev server reachable through Codespaces port forwarding.

Frappe's dev server listens on 0.0.0.0 (IPv4 only). Codespaces may connect to localhost
over IPv6 and then get nothing, which shows as HTTP 502 in the browser. This bridge pipes
bytes (including WebSocket upgrades) to the IPv4 server:

  PORT          listen on IPv6 [::]:PORT only (no clash with the IPv4 server on PORT)
  LISTEN:PORT   listen on LISTEN over IPv6 and IPv4, forward to 127.0.0.1:PORT

Usage: python3 ipv6_bridge.py 8000 9000 8080:8000
"""

import asyncio
import socket
import sys


async def _pipe(reader, writer):
	try:
		while data := await reader.read(65536):
			writer.write(data)
			await writer.drain()
	except (ConnectionError, OSError):
		pass
	finally:
		writer.close()


def _handler(target_port):
	async def handle(client_r, client_w):
		try:
			target_r, target_w = await asyncio.open_connection("127.0.0.1", target_port)
		except OSError:
			client_w.close()
			return
		await asyncio.gather(_pipe(client_r, target_w), _pipe(target_r, client_w))

	return handle


def _listen_socket(port, v6only):
	"""IPv6 socket (v6-only or dual-stack); IPv4 fallback for dual-stack if the host has no IPv6."""
	try:
		sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1 if v6only else 0)
		addr = ("::", port)
	except OSError:
		if v6only:
			return None  # no IPv6 on this machine: nothing to bridge
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		addr = ("0.0.0.0", port)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(addr)
	sock.listen(128)
	return sock


async def main(specs):
	servers = []
	for spec in specs:
		listen, _, target = spec.partition(":")
		listen, target = int(listen), int(target or listen)
		v6only = listen == target
		try:
			sock = _listen_socket(listen, v6only)
		except OSError as e:
			print(f"ipv6_bridge: port {listen}: {e} (already running?)", flush=True)
			continue
		if sock is None:
			print(f"ipv6_bridge: no IPv6 here, skipping {listen}", flush=True)
			continue
		servers.append(await asyncio.start_server(_handler(target), sock=sock))
		print(f"ipv6_bridge: {'[::]' if sock.family == socket.AF_INET6 else '0.0.0.0'}:{listen}"
		      f"{' (v6 only)' if v6only else ''} -> 127.0.0.1:{target}", flush=True)
	if servers:
		await asyncio.gather(*(s.serve_forever() for s in servers))


if __name__ == "__main__":
	asyncio.run(main(sys.argv[1:] or ["8000", "9000", "8080:8000"]))
