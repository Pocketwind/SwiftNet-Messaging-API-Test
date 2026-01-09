import socket, threading, base64, json,select, asyncio

from jwt import exceptions
import messaging.MessageMaker as MessageMaker

class AsyncSocketListener:
    def __init__(self,settings):
        self.host = settings.get("socketListenerHost", "0.0.0.0")
        self.port = int(settings.get("socketListenerPort", settings.get("socketListnerPort", 12345)))
        self.bufferSize = int(settings.get("socketBufferSize", 4096))
        self.encoding = settings.get("socketEncoding", "utf-8")
        self.server = None
        self.loop = None
        self._thread = None
        self.clients = {}
    async def HandleClient(self, reader, writer):
        addr = writer.get_extra_info("peername")
        self.clients[addr] = writer
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
            self.clients.pop(addr, None)
            writer.close()
            await writer.wait_closed()
    async def _proccess_line(self, writer, line, addr):
        try:
            text = line.decode(self.encoding, errors="replace").strip()
            MessageMaker.SocketJSONReceiver(text)
            #ACK response
            """
            response = f"ACK {res}".encode(self.encoding)
            writer.write(response + b"\n")
            await writer.drain()
            """
        except Exception as e:
            print("Decode Error: ", type(e).__name__, e)
    async def connect_and_send(self, host, port, message):
        try:
            reader, writer = await asyncio.open_connection(host, port)
            addr = writer.get_extra_info('peername')
            print(f"Outbound connected to {addr}")
            
            data = f"{message}\n".encode(self.encoding)
            writer.write(data)
            await writer.drain()
            
            # 옵션: 서버 응답 읽기
            #resp = await reader.read(self.bufferSize)
            #print(f"Outbound response: {resp.decode(errors='replace').strip()}")
            
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Outbound send error: {type(e).__name__} {e}")
    def Send(self, addr, port, data):
        if not self.loop or not self.loop.is_running():
            print("Event loop not ready")
            return None
        try:
            coro = self.connect_and_send(addr, port, data)
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result(timeout=10)  # 10초 타임아웃
        except Exception as e:
            print(f"Send external error: {type(e).__name__} {e}")
            return None

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