from sys import exception
import socket, threading, base64, json,select, asyncio, struct
from typing import final
import messaging.MessageMaker as MessageMaker

class AsyncSocketListener:
    def __init__(self,settings):
        self.host = settings.get("socketListenerHost", "0.0.0.0")
        self.port = int(settings.get("socketListenerPort", settings.get("socketListnerPort", 12345)))
        self.buffer_size = int(settings.get("socketBufferSize", 4096))
        self.encoding = settings.get("socketEncoding", "utf-8")
        self.settings = settings
        self.server = None
        self.loop = None
        self._thread = None
        self.clients = {}
    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        self.clients[addr] = writer
        buffer = b""
        print(f"Connection from {addr}", flush=True)

        try:
            try:
                first_chunk = await asyncio.wait_for(reader.read(self.buffer_size), timeout=3.0)
            except asyncio.TimeoutError:
                print(f"Connection timeout from {addr}")
                writer.close()
                await writer.wait_closed()
                return
            if not first_chunk:
                writer.close()
                return
            magic_byte = int(self.settings.get("magicByte", "0xEE"), 16)
            if first_chunk[0] == magic_byte:
                buffer = first_chunk
                is_http = False
            else:
                first_string = first_chunk[:10].decode(errors="ignore").upper()
                if any(first_string.startswith(m) for m in ["GET", "POST", "PUT", "DELETE", "HEAD", "OPT"]):
                    is_http = True
                else:
                    buffer = first_chunk
                    is_http = False

            # [분기 처리]
            if is_http:
                await self._process_http_request(reader, writer, first_chunk)
                return
            else:
                while True:
                    while len(buffer) >= 6:
                        magic, m_type, frame_len = struct.unpack('>BBI', buffer[:6])
                        total_packet_len = 6 + frame_len
                        
                        if len(buffer) < total_packet_len:
                            break
                        
                        frame = buffer[:total_packet_len]
                        buffer = buffer[total_packet_len:]
                        
                        await self._process_frame(writer, frame, addr)
                        continue # 버퍼에 남은 데이터가 또 있을 수 있으므로 반복

                    # 2. 추가 데이터 읽기
                    try:
                        data = await reader.read(self.buffer_size)
                    except ConnectionError:
                        break

                    if not data:
                        print(f"Disconnected {addr}", flush=True)
                        break
                    buffer += data
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("Socket Error:", type(e).__name__, e)
        finally:
            self.clients.pop(addr, None)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    async def _process_frame(self, writer, data, addr):
        #Incoming
        magic=int(self.settings.get("magicByte", "0xEE"), 16)
        try:
            #헤더 에러
            if len(data)<6:
                ack="Invalid Bytes".encode(self.encoding)
                raise Exception("Invalid Header")
            magic_received, message_type = struct.unpack(">BB", data[:2])
            #magic 에러
            if magic_received != magic:
                ack="Invalid Bytes".encode(self.encoding)
                raise Exception("Invalid Magic Bytes")
            #실제 데이터
            payload=data[6:]
            #message type: 1.json, 2.binary, 3.string, 4.json + hmac
            if message_type == 1:
                #JSON
                payload=payload.decode(self.encoding)
                payload=json.loads(payload)
            elif message_type == 2:
                #binary
                pass
            elif message_type == 3:
                #string
                payload=payload.decode(self.encoding)
            elif message_type == 4:
                #HMAC + JSON
                pass
            else:
                ack="Invalid Bytes".encode(self.encoding)
                raise Exception("Invalid Message Type")
        except Exception as e:
            print("_process_frame: ", type(e).__name__, e)
            #string으로 보내기
            """ack_header=struct.pack(">BBI", magic, 3, len(ack))
            ack_packet=ack_header+ack
            writer.write(ack_packet)
            await writer.drain()"""
        print(payload)
        ack="ACK".encode(self.encoding)
        ack_header=struct.pack(">BBI", magic, 3, len(ack))
        ack_packet=ack_header+ack
        writer.write(ack_packet)
        await writer.drain()
    async def _process_http_request(self, reader, writer, first_chunk):
        request_line = first_chunk.decode(errors='ignore').split('\n')[0]
        method_path = request_line.split()[:2]

        response = f"HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nReceived Path:{method_path}\r\n".encode()

        writer.write(response)
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    async def connect_and_send(self, host, port, data, message_type = 1):
        #Outgoing
        magic=int(self.settings.get("magicByte", "0xEE"), 16)
        try:
            reader, writer = await asyncio.open_connection(host, port)
            addr = writer.get_extra_info('peername')
            print(f"Sending binary data to {addr}")

            #message type: 1.json, 2.binary, 3.string, 4.json + hmac
            if message_type == 4:
                #HMAC + JSON 먼저 분기
                payload=data
                packet_header=struct.pack(">BBI", magic, 2, len(payload))
                packet_data=packet_header+payload
            elif isinstance(data, (dict, list)):
                #JSON
                payload=json.dumps(data, ensure_ascii=False).encode(self.encoding)
                packet_header=struct.pack(">BBI", magic, 1, len(payload))
                packet_data=packet_header+payload
            elif isinstance(data, bytes):
                #Binary
                payload=data
                packet_header=struct.pack(">BBI", magic, 2, len(payload))
                packet_data=packet_header+payload
            elif isinstance(data, str):
                #String
                payload=str(data).encode(self.encoding)
                packet_header=struct.pack(">BBI", magic, 3, len(payload))
                packet_data=packet_header+payload
            else:
                raise Exception("Unsupported Message Type")
        except Exception as e:
            print(f"connect_and_send Error: {e}")
            return None
        #데이터 전송
        writer.write(packet_data)
        await writer.drain()

        #ack 수신
        len_data = await asyncio.wait_for(reader.readexactly(6), timeout=5.0)
        _, _, ack_len = struct.unpack('>BBI', len_data)
        ack_bytes = await reader.readexactly(ack_len)
        ack = ack_bytes.decode(self.encoding, errors='replace').strip()

        writer.close()
        await writer.wait_closed()

        return ack
    def send(self, addr, port, data):
        if not self.loop or not self.loop.is_running():
            print("Event loop not ready")
            return None
        coro = self.connect_and_send(addr, port, data)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=10)
    async def MainLoop(self):
        try:
            self.loop = asyncio.get_running_loop()
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port,
                reuse_address=True,
                #reuse_port=True #리눅스만
            )
            print(f"Listening on {self.host}:{self.port}")
        except OSError as e:
            print(f"Bind failed: {e} - port {self.port} in use?")
            return
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
        asyncio.run(self.MainLoop())
    def stop(self, wait=True, timeout=5):
        """Gracefully stop the server and optionally wait for the thread to finish.
        - Closes the asyncio server in a thread-safe way
        - Waits for the thread to exit if wait=True
        """
        if self.server:
            try:
                if self.loop and self.loop.is_running():
                    # Schedule coroutine in the listener loop to close server and wait_closed
                    async def _close_server():
                        try:
                            self.server.close()
                            await self.server.wait_closed()
                        except Exception:
                            pass
                    try:
                        future = asyncio.run_coroutine_threadsafe(_close_server(), self.loop)
                        future.result(timeout=timeout)
                    except Exception:
                        pass
                    try:
                        # Stop the event loop so asyncio.run() returns
                        self.loop.call_soon_threadsafe(self.loop.stop)
                    except Exception:
                        pass
                else:
                    try:
                        self.server.close()
                    except Exception:
                        pass
            except Exception:
                pass

        # Wait for the worker thread to finish
        if wait and self._thread:
            self._thread.join(timeout)
            if self._thread.is_alive():
                print("SocketListener: thread did not exit within timeout")

    def join(self, timeout=None):
        """Wait for the listener thread to exit."""
        if self._thread:
            self._thread.join(timeout)

    def start(self):
        if self._thread and self._thread.is_alive():
            return  # 이미 실행 중
        def _run():
            try:
                asyncio.run(self.MainLoop())
            except Exception as e:
                print(e)
                # Ensure server is closed if MainLoop fails
                self.stop()
        # Start non-daemon thread so the listener can keep running until explicitly stopped
        self._thread = threading.Thread(target=_run, daemon=False)
        self._thread.start()
        print("SocketListener: thread started")


