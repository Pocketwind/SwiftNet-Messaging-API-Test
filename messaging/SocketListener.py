from math import e
import socket, threading, base64, json,select, asyncio

from requests.utils import address_in_network
from messaging.MessageMaker import *

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
            try:
                data = conn.recv(buffer_size)
                if not data:
                    # client closed connection
                    break
                try:
                    text = data.decode(encoding, errors="replace").strip()
                except Exception:
                    text = repr(data)
                print(f"SocketListener [{addr}]", flush=True)
                print(SocketJSONtoMT(text))
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
    #buffer_size = int(settings.get("socket_buffer_size", 4096))

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


class SocketListener:
    def __init__(self,settings):
        self.host=settings.get("socketListenerHost","0.0.0.0")
        self.port=int(settings.get("socketListnerPort",12345))
        self.bufferSize=int(settings.get("socketBufferSize",4096))
        self.stopEvent=threading.Event()
        self.server=None
        self.clients={}
    def stop(self):
        self.stopEvent.set()
        if self.server:
            self.server.close()
    def HandleClient(self,sock,data,addr):
        try:
            text = data.decode(self.encoding, errors='replace').strip()
            print(f"SocketListener [{addr}]", flush=True)
            print(text)
        except Exception as e:
            print("SocketListener: client handler error:", type(e).__name__, e)
    def Loop(self):
        self.server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind((self.host,self.port))
            self.server.listen(5)
            self.server.settimeout(1.0)
            print(f"SocketListener: Listening on {self.host}:{self.port}")
            while not self.stopEvent.is_set():
                serverList=[self.server]+list(self.clients.keys())
                r,w,_=select.select(serverList,[],[],1.0)
                for sock in r:
                    if sock == self.server:
                        con,addr=self.server.accept()
                        self.clients[con]=addr
                    elif sock in self.clients:
                        addr,partial=self.clients[sock]
                        try:
                            data=sock.recv(self.bufferSize)
                            if not data:
                                del self.clients[sock]
                                sock.close()
                                continue
                            partial+=data
                        except Exception as e:
                            print("SocketListener: recv error:", type(e).__name__, e)
                            del self.clients[sock]
                            sock.close()
                            continue
        except Exception as e:
            print("SocketListener: failed to bind/listen:", type(e).__name__, e)
        finally:
            self.server.close()
            for sock in self.clients.keys():
                sock.close()

class AsyncSocketListener:
    def __init__(self,settings):
        self.host = settings.get("socketListenerHost", "0.0.0.0")
        self.port = int(settings.get("socketListenerPort", settings.get("socketListnerPort", 12345)))
        self.bufferSize = int(settings.get("socketBufferSize", 4096))
        self.encoding = settings.get("socketEncoding", "utf-8")
        self.server = None
        self.loop = None
        self._thread = None
    async def HandleClient(self, reader, writer):
        addr = writer.get_extra_info("peername")
        partialBuffer = b""
        print(f"Connection from {addr}", flush=True)
        try:
            while True:
                data = await reader.read(self.bufferSize)
                if not data:
                    if partialBuffer:
                        await self._proccess_line(writer, bytes(partialBuffer), addr)
                    print(f"Disconnected {addr}", flush=True)
                    break
                partialBuffer+=data
                while b"\n" in partialBuffer:
                    newline = partialBuffer.find(b"\n")
                    line = partialBuffer[:newline]
                    partialBuffer = partialBuffer[newline + 1:]
                    await self._proccess_line(writer, line, addr)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("Socket Error:", type(e).__name__, e)
        finally:
            writer.close()
            await writer.wait_closed()
    async def _proccess_line(self, writer, line, addr):
        try:
            text = line.decode(self.encoding, errors="replace").strip()
            SocketJSONtoMT(text)
        except Exception as e:
            print("Decode Error: ", type(e).__name__, e)
    async def MainLoop(self):
        self.loop = asyncio.get_running_loop()
        self.server = await asyncio.start_server(
            self.HandleClient, self.host, self.port
        )
        print(f"Listening on {self.host}:{self.port}")
        try:
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            # serve_forever()가 취소된 경우(예: Ctrl+C/KeyboardInterrupt), 조용히 종료
            pass
        finally:
            try:
                if self.server:
                    self.server.close()
                    await self.server.wait_closed()
            except Exception:
                pass
            #print("SocketListener: MainLoop stopped")
    def main(self):
        try:
            asyncio.run(self.MainLoop())
        except KeyboardInterrupt:
            # Ctrl+C로 인한 KeyboardInterrupt를 억제하여 traceback이 출력되지 않도록 함
            pass
    def stop(self):
        if self.server:
            try:
                if self.loop:
                    # Event loop가 별도 스레드에서 실행 중이면 스레드 안전하게 서버 닫기
                    self.loop.call_soon_threadsafe(self.server.close)
                else:
                    self.server.close()
            except Exception:
                pass
    def start(self):
        def _run():
            asyncio.run(self.MainLoop())
        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()    