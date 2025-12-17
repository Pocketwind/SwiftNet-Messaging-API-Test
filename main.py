import Authorization as auth
from messaging.Retrieve import *
from messaging.Download import *
from messaging.SingleSend import *
from messaging.FileAct import *
from messaging.Watchdog import *
from messaging.MessageMaker import *
import json, threading, time, os, warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

#settings에서 설정 값 읽어오기
with open("settings.json","r") as f:
    settings=json.load(f)

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
    #Ctrl+C로 종료시 이벤트 
    stop_event = threading.Event()
    #스레드 시작
    #파일 탐지 위한 스레드 정의/시작
    #SingleSend Thread
    if settings["singleSendService"]:
        print("---------------------------------------------------------------")
        print("Starting SingleSend Service...")
        singleSendThread = threading.Thread(target=ThreadWatchdog, args=(settings["inputPath"], MessageInputCallback, stop_event))
        singleSendThread.start()
        print("SingleSend Service Started. Monitoring directory is:\n", settings["inputPath"])
        print("---------------------------------------------------------------")
    #FileAct Thread
    if settings["fileActService"]:
        print("---------------------------------------------------------------")
        print("Starting FileAct Service")
        fileActThread = threading.Thread(target=ThreadWatchdog, args=(settings["fileActInputPath"], FileInputCallback, stop_event))
        fileActThread.start()
        print("FileAct Service Started. Monitoring directory is:\n", settings["fileActInputPath"])
        print("---------------------------------------------------------------")
    #Distribution Thread
    if settings["distService"]:
        print("---------------------------------------------------------------")
        print("Starting Distribution Service...")
        distributionThread = threading.Thread(target=ThreadRetrieve, args=(settings, stop_event))
        distributionThread.start()
        print("Distribution Service Started.")
        print("---------------------------------------------------------------")
    #Download Thread
    if settings["downloadService"]:
        print("---------------------------------------------------------------")
        print("Starting Download Service...")
        downloadThread=threading.Thread(target=ThreadDownload, args=(settings, stop_event))
        downloadThread.start()
        print("Download Service Started.")
        print("---------------------------------------------------------------")
    #MessageMaker Thread
    if settings["messageMakerService"]:
        print("---------------------------------------------------------------")
        print("Starting MessageMaker Service...")
        messageMakerThread=threading.Thread(target=ThreadMessageMaker, args=(settings, MessageMakerCallback, stop_event))
        messageMakerThread.start()
        print("MessageMaker Service Started.")
        print("---------------------------------------------------------------")

    while True:
        #Main Thread
        #Refresh
        #토큰 만료 시간마다 Refresh 하기 -> 이전 토큰값은 자동으로 폐기됨
        accessToken = auth.Auth(True, settings)
        SetAccessToken(accessToken)
        #만료시간까지 Refresh 중지
        time.sleep(settings["expirationTime"])

except KeyboardInterrupt:
    #Ctrl+C 입력 감지
    print("---------------------------------------------------------------")
    print("Stopping All Services...")
    print("---------------------------------------------------------------")
finally:
    #서비스(스레드) 모두 종료
    if settings["singleSendService"]:
        print("---------------------------------------------------------------")
        print("Stopping SingleSend Service...")
        stop_event.set()            
        singleSendThread.join(timeout=5) 
        print("SingleSend Service Stopped.")
        print("---------------------------------------------------------------")
    if settings["fileActService"]:
        print("---------------------------------------------------------------")
        print("Stopping FileAct Service...")
        stop_event.set()            
        fileActThread.join(timeout=5) 
        print("FileAct Service Stopped.")
        print("---------------------------------------------------------------")
    if settings["distService"]:
        print("---------------------------------------------------------------")
        print("Stopping Distribution Service...")
        stop_event.set()            
        distributionThread.join(timeout=5)
        print("Distribution Service Stopped.")
        print("---------------------------------------------------------------")
    if settings["downloadService"]:
        print("---------------------------------------------------------------")
        print("Stopping Download Service...")
        stop_event.set()
        downloadThread.join(timeout=5)
        print("Download Service Stopped.")
        print("---------------------------------------------------------------")
    if settings["messageMakerService"]:
        print("---------------------------------------------------------------")
        print("Stopping MessageMaker Service...")
        stop_event.set()
        messageMakerThread.join(timeout=5)
        print("MessageMaker Service Stopped.")
        print("---------------------------------------------------------------")
    #사용중이던 토큰 폐기
    print("---------------------------------------------------------------")
    print("Revoking Access Token...")
    RevokeToken(settings)
    print("Success")    
    print("---------------------------------------------------------------")
    print("Program has terminated successfully")