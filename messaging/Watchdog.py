from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

#파일 감지 시 사용하는 이벤트 처리 파트
class FileEventHandler(FileSystemEventHandler):
    def __init__(self, inputCallback):
        self.InputCallback = inputCallback
    def on_created(self, event):
        print(f"Watchdog - File detected: {event.src_path}")
        #파일 생성(이동) 시 발생하는 onCreate 이벤트는 데이터 완전히 이동 전에 호출됨
        #완전히 이동하기까지 일정 시간 기다려야 하는데 서버 성능마다 다를듯
        #ex) HDD를 사용한다면 MX같은 긴 메시지는 길게 wait 걸어야함
        #개인 노트북으로 테스트 시 SSD에서는 오류X, HDD는 파일 IO 오류 발생
        time.sleep(0.1)
        self.InputCallback(event.src_path)


def ThreadWatchdog(path, inputCallback, stopEvent):
    eventHandler=FileEventHandler(inputCallback)
    observer=Observer()
    observer.schedule(eventHandler, path, recursive=False)
    observer.start()
    try:
        while not stopEvent.is_set():
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()

def ThreadMessageMaker(settings, inputCallback, stopEvent):
    eventHandler=FileEventHandler(inputCallback)
    observer=Observer()
    observer.schedule(eventHandler, settings["downloadPath"], recursive=False)
    observer.start()
    try:
        while not stopEvent.is_set():
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()