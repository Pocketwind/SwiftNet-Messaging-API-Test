import Auth.Authorization as auth
from messaging.Retrieve import *
from messaging.Download import *
from messaging.SingleSend import *
from messaging.FileAct import *
from messaging.Watchdog import *
from messaging.MessageMaker import *
from messaging.SocketListener import *
import json, threading, time, os, warnings
from Data.globalData import *
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

#settings에서 설정 값 읽어오기
with open("settings.json","r") as f:
    settings=json.load(f)
with open(settings["certificatePath"], "r") as f:
    certificate=f.read()
with open(settings["privatePath"], "r") as f:
    private=f.read()
SetCertificate(certificate)
SetPrivateKey(private)

#스레드 콜백 정의 부분
#파이썬에선 이렇게 할 필요는 없지만 C나 Java(?) 에서는 스레드에서 path값 넘겨주기 위해 임시 사용
#메시지 파일 In/Out 탐지 
def MessageInputCallback(path):
    MessageCollector(path, settings)
def MessageMakerCallback(downloadPath):
    MessageMaker(downloadPath, settings["outputPath"], settings["ackPath"])
def FileInputCallback(path):
    FileCollector(path, settings)


try:
    #Access Token(JWT) 받아오기 위한 Auth
    accessToken = auth.Auth(True, settings)
    SetAccessToken(accessToken)
    #Ctrl+C로 종료시 이벤트 
    stop_event = threading.Event()
    #스레드 시작
    #파일 탐지 위한 스레드 정의/시작
    #SingleSend Thread
    if settings["singleSendService"]:
        print("Starting SingleSend Service...")
        singleSendThread = threading.Thread(target=ThreadWatchdog, args=(settings["inputPath"], MessageInputCallback, stop_event))
        singleSendThread.start()
        print("SingleSend Service Started. Monitoring directory is: ", settings["inputPath"])
    #FileAct Thread
    if settings["fileActService"]:
        print("Starting FileAct Service")
        fileActThread = threading.Thread(target=ThreadWatchdog, args=(settings["fileActInputPath"], FileInputCallback, stop_event))
        fileActThread.start()
        print("FileAct Service Started. Monitoring directory is: ", settings["fileActInputPath"])
    #Distribution Thread
    if settings["distService"]:
        print("Starting Distribution Service...")
        distributionThread = threading.Thread(target=ThreadRetrieve, args=(settings, stop_event))
        distributionThread.start()
        print("Distribution Service Started.")
    #Download Thread
    if settings["downloadService"]:
        print("Starting Download Service...")
        downloadThread=threading.Thread(target=ThreadDownload, args=(settings, stop_event))
        downloadThread.start()
        print("Download Service Started.")
    #MessageMaker Thread
    if settings["messageMakerService"]:
        print("Starting MessageMaker Service...")
        messageMakerThread=threading.Thread(target=ThreadMessageMaker, args=(settings, MessageMakerCallback, stop_event))
        messageMakerThread.start()
        print("MessageMaker Service Started.")
    # Socket Listener Thread
    if settings.get("socketListenerService", False):
        print("Starting Socket Listener Service...")
        socketListenerThread = threading.Thread(target=ThreadSocketListener, args=(settings, stop_event))
        socketListenerThread.start()
        print("Socket Listener Service Started.")
    #Token Refresh Thread
    tokenRefreshThread=threading.Thread(target=ThreadTokenRefresh, args=(settings, stop_event))
    tokenRefreshThread.start()

    while True:
        #Main Thread
        time.sleep(1)

except KeyboardInterrupt:
    #Ctrl+C 입력 감지
    print("---------------------------------------------------------------")
    print("Stopping All Services...")
    print("---------------------------------------------------------------")
finally:
    #서비스(스레드) 모두 종료
    if settings["singleSendService"]:
        print("Stopping SingleSend Service...")
        stop_event.set()            
        singleSendThread.join(timeout=5) 
        print("SingleSend Service Stopped.")
    if settings["fileActService"]:
        print("Stopping FileAct Service...")
        stop_event.set()            
        fileActThread.join(timeout=5) 
        print("FileAct Service Stopped.")
    if settings["distService"]:
        print("Stopping Distribution Service...")
        stop_event.set()            
        distributionThread.join(timeout=5)
        print("Distribution Service Stopped.")
    if settings["downloadService"]:
        print("Stopping Download Service...")
        stop_event.set()
        downloadThread.join(timeout=5)
        print("Download Service Stopped.")
    if settings["messageMakerService"]:
        print("Stopping MessageMaker Service...")
        stop_event.set()
        messageMakerThread.join(timeout=5)
        print("MessageMaker Service Stopped.")
    if settings["socketListenerService"]:
        print("Stopping Socket Listener Service...")
        stop_event.set()
        socketListenerThread.join(timeout=5)
        print("Socket Listener Service Stopped.")
    #Token Refresh Thread 종료
    stop_event.set()
    tokenRefreshThread.join(timeout=5)
    #사용중이던 토큰 폐기
    print("Revoking Access Token...")
    RevokeToken(settings)
    print("Success")
    print("Program has terminated successfully")