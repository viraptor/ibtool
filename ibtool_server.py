#!/usr/bin/env python3
"""TCP socket server that runs /usr/bin/ibtool on behalf of clients."""

import json
import os
import selectors
import socket
import subprocess
import sys
import threading


def handle_client(conn):
    """Handle a single client connection."""
    try:
        # Read the command line from the client (newline-terminated JSONL)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk

        line, _ = buf.split(b"\n", 1)
        request = json.loads(line)
        args = request.get("args", [])
        if args[0] == '/usr/bin/ibtool':
            pass
        elif args[0] == '/usr/bin/test.py':
            args[0] = './test.py'
        else:
            print("wrong tool, refusing")
            return

        print("running", args)
        cmd = args
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
        sel.register(proc.stderr, selectors.EVENT_READ, "stderr")

        open_count = 2
        while open_count > 0:
            for key, _ in sel.select():
                chunk = key.fileobj.read1(8192) if hasattr(key.fileobj, "read1") else os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    sel.unregister(key.fileobj)
                    open_count -= 1
                else:
                    msg = json.dumps({key.data: chunk.decode("utf-8", errors="replace")}) + "\n"
                    conn.sendall(msg.encode("utf-8"))

        sel.close()
        exit_code = proc.wait()
        msg = json.dumps({"finish": exit_code}) + "\n"
        conn.sendall(msg.encode("utf-8"))
    except Exception as e:
        try:
            msg = json.dumps({"stderr": f"server error: {e}\n"}) + "\n"
            conn.sendall(msg.encode("utf-8"))
            conn.sendall((json.dumps({"finish": 1}) + "\n").encode("utf-8"))
        except Exception:
            pass
    finally:
        conn.close()


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <host:port>", file=sys.stderr)
        sys.exit(1)

    os.environ["LANG"] = "en_US"
    os.environ["LC_ALL"] = "en_US_POSIX"
    os.environ["TZ"] = "Etc/UTC"

    host, port = sys.argv[1].rsplit(":", 1)
    port = int(port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    print(f"Listening on {host}:{port}", file=sys.stderr)

    try:
        while True:
            conn, _ = sock.accept()
            t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
            t.start()
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()
