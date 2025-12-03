from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time, os, json

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, inputCallback):
        self.InputCallback = inputCallback
    def on_created(self, event):
        print(f"Watchdog - File detected: {event.src_path}")
        time.sleep(0.01)  # Wait a moment to ensure file is fully written
        #print('Invoking input callback...')
        self.InputCallback(event.src_path)


def ThreadSingleSend(path, inputCallback, stopEvent):
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