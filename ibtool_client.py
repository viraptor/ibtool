#!/usr/bin/env python3
"""TCP socket client that sends args to ibtool_server and relays output."""

import json
import os
import socket
import sys


def main():
    addr = os.environ.get("IBTOOL_SOCKET", "host.docker.internal:9123")
    if not addr:
        print("Error: IBTOOL_SOCKET environment variable not set", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[:]

    host, port = addr.rsplit(":", 1)
    port = int(port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    request = json.dumps({"args": args}) + "\n"
    sock.sendall(request.encode("utf-8"))

    buf = b""
    while True:
        chunk = sock.recv(8192)
        if not chunk:
            # Server closed connection unexpectedly
            sys.exit(1)
        buf += chunk

        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            msg = json.loads(line)

            if "stdout" in msg:
                sys.stdout.write(msg["stdout"])
                sys.stdout.flush()
            elif "stderr" in msg:
                sys.stderr.write(msg["stderr"])
                sys.stderr.flush()
            elif "finish" in msg:
                sock.close()
                sys.exit(msg["finish"])

    sock.close()
    sys.exit(1)


if __name__ == "__main__":
    main()
