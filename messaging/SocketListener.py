import threading, json, asyncio, struct
import messaging.MessageMaker as MessageMaker
import data.hmacValidation as hv
from data.enums import MessageType

class AsyncSocketListener:
    def __init__(self,settings):
        self.host = settings.get("socketListenerHost", "0.0.0.0")
        self.port = int(settings.get("socketListenerPort", 12345))
        self.buffer_size = int(settings.get("socketBufferSize", 4096))
        self.encoding = settings.get("socketEncoding", "utf-8")
        self.settings = settings
        self.magic_bytes = int(settings.get("magicByte", "0xEE"), 16)
        self.server = None
        self.loop = None
        self._thread = None
        self.clients = {}
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        self.clients[addr] = writer
        print(f"Connection from {addr}", flush=True)

        # 반드시 close 되도록 보장 (RAII 패턴)
        try:
            buffer = b""

            # 1. 첫 번째 청크 타임아웃 처리
            try:
                first_chunk = await asyncio.wait_for(reader.read(self.buffer_size), timeout=5.0)
            except asyncio.TimeoutError:
                print(f"Initial timeout from {addr}", flush=True)
                return

            if not first_chunk:
                return  # EOF

            # 2. HTTP vs Custom 프로토콜 분기
            if first_chunk[0] == self.magic_bytes:
                buffer = first_chunk
                is_http = False
            else:
                # HTTP인지 간단히 체크
                preview = first_chunk[:20].decode(errors="ignore").upper()
                is_http = any(preview.startswith(m) for m in ("GET ", "POST ", "PUT ", "DELETE ", "HEAD ", "OPTIONS ", "PATCH "))
            
            if is_http:
                await self._process_http_request(reader, writer, first_chunk)
                return

            # 3. Custom 프로토콜 처리 루프
            while True:
                # 버퍼에 완성된 패킷이 있는지 확인
                while len(buffer) >= 6:
                    try:
                        magic, m_type, frame_len = struct.unpack('>BBI', buffer[:6])
                    except struct.error:
                        # 헤더 깨짐 → 연결 종료
                        print(f"Header parse error from {addr}", flush=True)
                        return

                    total_len = 6 + frame_len
                    if len(buffer) < total_len:
                        break

                    frame = buffer[:total_len]
                    buffer = buffer[total_len:]

                    await self._process_frame(writer, frame, addr)

                # 더 데이터 읽기 (타임아웃 포함)
                try:
                    data = await asyncio.wait_for(reader.read(self.buffer_size), timeout=30.0)
                except asyncio.TimeoutError:
                    print(f"Read timeout from {addr}, closing", flush=True)
                    return
                except (ConnectionResetError, asyncio.IncompleteReadError):
                    print(f"Connection reset by {addr}", flush=True)
                    return

                if not data:  # EOF
                    print(f"Client {addr} disconnected cleanly", flush=True)
                    return

                buffer += data

        except asyncio.CancelledError:
            # task가 취소된 경우 (서버 종료 시) 조용히 종료
            print(f"handle_client cancelled for {addr}", flush=True)
            raise  # 반드시 다시 raise 해야 task가 완전히 정리됨
        except Exception as e:
            print(f"Unhandled exception in handle_client {addr}: {type(e).__name__}: {e}", flush=True)
        finally:
            self.clients.pop(addr, None)

            if not writer.is_closing():
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=3.0)
                except Exception:
                    pass
            print(f"Connection closed: {addr}", flush=True)
    async def _process_frame(self, writer, data, addr):
        #Incoming
        try:
            #헤더 에러
            if len(data)<6:
                ack="Invalid Bytes".encode(self.encoding)
                raise Exception("Invalid Header")
            magic_received, message_type = struct.unpack(">BB", data[:2])
            #magic 에러
            if magic_received != self.magic_bytes:
                ack="Invalid Bytes".encode(self.encoding)
                raise Exception("Invalid Magic Bytes")
            #실제 데이터
            payload=data[6:]
            #message type: 1.json, 2.binary, 3.string, 4.json + hmac
            if message_type == MessageType.JSON:
                #JSON
                payload=payload.decode(self.encoding)
                payload=json.loads(payload)
                ack="ACK"
            elif message_type == MessageType.BINARY:
                #binary
                pass
            elif message_type == MessageType.STRING:
                #string
                payload=payload.decode(self.encoding)
            elif message_type == MessageType.HMAC_STRING:
                #HMAC + STRING
                result = hv.validation(payload, self.settings["hmacSecret"])
                if result:
                    print("Validated")
                    payload=hv.decode(payload, self.settings["hmacSecret"])
                else:
                    ack="Invalid HMAC Signature".encode(self.encoding)
                    raise Exception("Invalid HMAC Signature")
            else:
                ack="Invalid Bytes".encode(self.encoding)
                raise Exception("Invalid Message Type")
        except Exception as e:
            print("_process_frame: ", type(e).__name__, e)
            #string으로 보내기
            ack_header=struct.pack(">BBI", self.magic_bytes, MessageType.STRING, len(ack))
            ack_packet=ack_header+ack
            writer.write(ack_packet)
            await writer.drain()
            return
        print(payload)
        ack="ACK".encode(self.encoding)
        ack_header=struct.pack(">BBI", self.magic_bytes, MessageType.STRING, len(ack))
        ack_packet=ack_header+ack
        writer.write(ack_packet)
        await writer.drain()
        return
    async def _process_http_request(self, reader, writer, first_chunk):
        buffer=bytearray(first_chunk)
        while True:
            if b"\r\n\r\n" in buffer:
                break
            chunk = await asyncio.wait_for(reader.read(8192), timeout=10.0)
            if not chunk:
                break
            buffer.extend(chunk)

        header_end = buffer.find(b"\r\n\r\n")
        headers_bytes = buffer[:header_end]
        body_bytes = buffer[header_end + 4:]

        headers_text = headers_bytes.decode('utf-8', errors='ignore')
        body_text = body_bytes.decode('utf-8', errors='ignore')

        headers_text = headers_bytes.decode('utf-8', errors='ignore')
        headers = {}
        for line in headers_text.splitlines()[1:]:  # 첫 줄은 Request-Line
            if not line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0"))  # 없으면 0
        while len(body_bytes) < content_length:
            need = content_length - len(body_bytes)
            chunk = await asyncio.wait_for(reader.read(need), timeout=10.0)
            if not chunk:
                break
            body_bytes.extend(chunk)

        json_received = None
        if content_length > 0 and "application/json" in headers.get("content-type", ""):
            body_str = body_bytes.decode('utf-8')
            json_received = json.loads(body_str)

        request_line = headers_text.splitlines()[0]
        method, path, _ = request_line.split()[:3]

        response_data = {
            "message": "OK",
            "method": method,
            "path": path,
            "received_body": json_received  # None 이거나 파싱된 JSON
        }

        response_body = json.dumps(response_data, ensure_ascii=False, indent=None).encode('utf-8')
        

        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode() + response_body

        writer.write(response)
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    async def connect_and_send(self, host, port, data, message_type = 1):
        #Outgoing

        try:
            reader, writer = await asyncio.open_connection(host, port)
            addr = writer.get_extra_info('peername')
            print(f"Sending binary data to {addr}")

            #message type: 1.json, 2.binary, 3.string, 4.json + hmac
            if message_type == MessageType.HMAC_STRING:
                #HMAC 먼저 분기
                payload=data
                packet_header=struct.pack(">BBI", self.magic_bytes, MessageType.HMAC_STRING, len(payload))
                packet_data=packet_header+payload
            elif isinstance(data, (dict, list)):
                #JSON
                payload=json.dumps(data, ensure_ascii=False).encode(self.encoding)
                packet_header=struct.pack(">BBI", self.magic_bytes, MessageType.JSON, len(payload))
                packet_data=packet_header+payload
            elif isinstance(data, bytes):
                #Binary
                payload=data
                packet_header=struct.pack(">BBI", self.magic_bytes, MessageType.BINARY, len(payload))
                packet_data=packet_header+payload
            elif isinstance(data, str):
                #String
                payload=str(data).encode(self.encoding)
                packet_header=struct.pack(">BBI", self.magic_bytes, MessageType.STRING, len(payload))
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
    def send(self, addr, port, data, message_type = 1):
        if not self.loop or not self.loop.is_running():
            print("Event loop not ready")
            return None
        coro = self.connect_and_send(addr, port, data, message_type)
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
    def stop(self, wait=True, timeout=10):
        if self.server:
            self.server.close()

        # 모든 클라이언트 강제 종료
        for writer in list(self.clients.values()):
            if not writer.is_closing():
                writer.close()

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._force_close_all(), self.loop)

    async def _force_close_all(self):
        tasks = [w.wait_closed() for w in self.clients.values() if not w.is_closing()]
        if tasks:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=3)
        if self.server:
            await self.server.wait_closed()
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


