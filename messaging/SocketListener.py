import socket, threading, base64

# Threaded socket listener that accepts TCP connections and prints received messages in real time
# settings expects:
#   - socket_listen_host: host to bind (default 0.0.0.0)
#   - socket_listen_port: port to bind (default 12345)
#   - socket_buffer_size: recv buffer size (default 4096)
#   - socket_encoding: decode encoding (default utf-8)


def handle_client(conn, addr, settings, stopEvent):
    buffer_size = int(settings.get("socket_buffer_size", 4096))
    encoding = settings.get("socket_encoding", "utf-8")
    print(f"SocketListener: Client connected from {addr}")
    try:
        conn.settimeout(1.0)
        while not stopEvent.is_set():
            print("123123")
            try:
                data = conn.recv(buffer_size)
                if not data:
                    # client closed connection
                    break
                try:
                    text = data.decode(encoding, errors="replace").strip()
                except Exception:
                    text = repr(data)
                print(f"SocketListener [{addr}]:\n{text}", flush=True)
            except socket.timeout:
                continue
            except Exception as e:
                print("SocketListener: client handler error:", type(e).__name__, e)
                break
    finally:
        try:
            conn.close()
        except Exception:
            pass
        print(f"SocketListener: Client disconnected {addr}")


def ThreadSocketListener(settings, stopEvent):
    host = settings.get("socket_listen_host", "0.0.0.0")
    port = int(settings.get("socket_listen_port", 12345))
    buffer_size = int(settings.get("socket_buffer_size", 4096))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((host, port))
        server.listen(5)
    except Exception as e:
        print("SocketListener: failed to bind/listen:", type(e).__name__, e)
        return

    print(f"SocketListener: Listening on {host}:{port}")
    server.settimeout(1.0)  # short timeout to check stopEvent frequently

    client_threads = []

    try:
        while not stopEvent.is_set():
            try:
                conn, addr = server.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr, settings, stopEvent), daemon=True)
                t.start()
                client_threads.append(t)
            except socket.timeout:
                continue
            except Exception as e:
                print("SocketListener: accept error:", type(e).__name__, e)
                break
    finally:
        try:
            server.close()
        except Exception:
            pass
        # wait for client threads to finish (short join)
        for t in client_threads:
            t.join(timeout=1)
        #print("SocketListener: Stopped")
