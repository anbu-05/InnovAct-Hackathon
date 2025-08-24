#!/usr/bin/env python3
# laptop_server.py - simple multi-client TCP server that prints and saves received bytes

import socketserver
import argparse
import datetime
import sys

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"Connected: {peer}")
        try:
            while True:
                data = self.request.recv(4096)
                if not data:
                    break
                ts = datetime.datetime.now().isoformat(timespec='seconds')
                print(f"[{ts}] {peer} {len(data)} bytes -> {data.hex()}")
                with open("received.bin", "ab") as f:
                    f.write(data)
        except Exception as e:
            print("Handler error:", e)
        finally:
            print(f"Disconnected: {peer}")

def main():
    p = argparse.ArgumentParser(description="Laptop TCP server for ESP relay")
    p.add_argument("--host", default="0.0.0.0", help="Host/IP to bind (use your laptop AP IP)")
    p.add_argument("--port", type=int, default=9000, help="Port to listen on")
    args = p.parse_args()

    server = socketserver.ThreadingTCPServer((args.host, args.port), Handler)
    server.allow_reuse_address = True
    print(f"Listening on {args.host}:{args.port}  -> output file: received.bin")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.shutdown()
        server.server_close()
        sys.exit(0)

if __name__ == "__main__":
    main()
