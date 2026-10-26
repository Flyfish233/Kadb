#!/usr/bin/env python3
"""Loopback-only, byte-preserving ADB relay; records headers, never payloads or keys."""

from __future__ import annotations

import collections
import select
import socket
import socketserver
import struct
import threading


class FrameObserver:
    COMMANDS = {b"CNXN", b"AUTH", b"OPEN", b"OKAY", b"CLSE", b"WRTE", b"STLS"}

    def __init__(self, record):
        self.record = record
        self.header = bytearray()
        self.remaining = 0
        self.opaque = False

    def feed(self, data: bytes) -> None:
        while data and not self.opaque:
            if self.remaining:
                length = min(len(data), self.remaining)
                self.remaining -= length
                data = data[length:]
                continue
            length = min(24 - len(self.header), len(data))
            self.header.extend(data[:length])
            data = data[length:]
            if len(self.header) != 24:
                continue
            command, arg0, arg1, payload_length, checksum, magic = struct.unpack("<6I", self.header)
            command_bytes = bytes(self.header[:4])
            self.header.clear()
            if magic != command ^ 0xFFFFFFFF or command_bytes not in self.COMMANDS or payload_length > 16 * 1024 * 1024:
                self.record({"error": "invalid_plaintext_adb_header"})
                self.opaque = True
                return
            self.record({"command": command_bytes.decode("ascii"), "arg0": arg0, "arg1": arg1,
                         "payload_length": payload_length})
            self.remaining = payload_length
            # Following bytes belong to TLS, not ADB headers. Do not inspect TLS payloads.
            if command_bytes == b"STLS":
                self.opaque = True


class AdbRelay:
    def __init__(self, target_port: int):
        self.target_port = target_port
        self.lock = threading.Lock()
        self.counts = collections.Counter()
        self.events = []
        self.errors = []
        self.connections = 0
        self.sockets = set()
        owner = self

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            block_on_close = False

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                owner.handle(self.request)

        self.server = Server(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)

    def record(self, connection: int, direction: str, event: dict) -> None:
        with self.lock:
            event = {"connection": connection, "direction": direction, **event}
            if "error" in event:
                self.errors.append(event)
            else:
                self.counts[f"{direction}:{event['command']}"] += 1
                if event["command"] == "AUTH":
                    self.counts[f"{direction}:AUTH:{event['arg0']}"] += 1
            if len(self.events) < 512:
                self.events.append(event)

    def handle(self, incoming: socket.socket) -> None:
        outgoing = None
        with self.lock:
            self.connections += 1
            connection = self.connections
            self.sockets.add(incoming)
        try:
            outgoing = socket.create_connection(("127.0.0.1", self.target_port), timeout=10)
            outgoing.settimeout(None)
            with self.lock:
                self.sockets.add(outgoing)
            peers = {incoming: outgoing, outgoing: incoming}
            observers = {
                incoming: FrameObserver(lambda event: self.record(connection, "host_to_adbd", event)),
                outgoing: FrameObserver(lambda event: self.record(connection, "adbd_to_host", event)),
            }
            readable = list(peers)
            while readable:
                ready, _, _ = select.select(readable, [], [], 1)
                for source in ready:
                    data = source.recv(64 * 1024)
                    if not data:
                        readable.remove(source)
                        try:
                            peers[source].shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        continue
                    observers[source].feed(data)
                    peers[source].sendall(data)
        except (ConnectionError, OSError, ValueError):
            # Peer shutdown/reset is part of the cancellation and close contract.
            # Successful consumer checks, not a relay exit, decide product health.
            pass
        finally:
            for endpoint in (incoming, outgoing):
                if endpoint is not None:
                    with self.lock:
                        self.sockets.discard(endpoint)
                    endpoint.close()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        with self.lock:
            endpoints = list(self.sockets)
        for endpoint in endpoints:
            try:
                endpoint.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.thread.join(timeout=5)

    def snapshot(self) -> dict:
        with self.lock:
            return {"connections": self.connections, "counts": dict(self.counts),
                    "header_errors": list(self.errors), "first_events": list(self.events)}
