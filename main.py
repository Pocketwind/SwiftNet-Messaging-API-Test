import pip_system_certs.wrapt_requests
pip_system_certs.wrapt_requests.inject_truststore()
import auth.Authorization as Auth
import auth.Token as Token
import messaging.Retrieve as Retrieve
import messaging.Download as Download
import messaging.SingleSend as SingleSend
import messaging.FileAct as FileAct
import messaging.Watchdog as Watchdog
import messaging.MessageMaker as MessageMaker
import messaging.SocketListener as Socket
import data.globalData as Data
import json, threading, time, os, warnings, pip_system_certs, asyncio
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

with open("settings.json","r") as f:
    settings=json.load(f)
with open(settings["certificatePath"], "r") as f:
    certificate=f.read()
with open(settings["privatePath"], "r") as f:
    private=f.read()
Data.SetCertificate(certificate)
Data.SetPrivateKey(private)
Data.SetSettings(settings)

os.makedirs(settings["inputPath"], exist_ok=True)
os.makedirs(settings["outputPath"], exist_ok=True)
os.makedirs(settings["fileActInputPath"], exist_ok=True)
os.makedirs(settings["fileActOutputPath"], exist_ok=True)
os.makedirs(settings["ackPath"], exist_ok=True)
os.makedirs(settings["downloadPath"], exist_ok=True)

def MessageInputCallback(path):
    SingleSend.MessageCollector(path, settings)
def MessageMakerCallback(downloadPath):
    MessageMaker.MessageMaker(downloadPath, settings, asyncSocketListener.Send)
def FileInputCallback(path):
    FileAct.FileCollector(path, settings)
try:
    accessToken = Auth.Auth(True, settings)
    Data.SetAccessToken(accessToken)
    stop_event = threading.Event()

    #Distribution Thread
    if settings["distService"]:
        print("Starting Distribution Service...")
        distributionThread = threading.Thread(target=Retrieve.ThreadRetrieve, args=(settings, stop_event))
        distributionThread.start()
        print("Distribution Service Started.")
    #SingleSend Thread
    if settings["singleSendService"]:
        print("Starting SingleSend Service...")
        singleSendThread = threading.Thread(target=Watchdog.ThreadWatchdog, args=(settings["inputPath"], MessageInputCallback, stop_event))
        singleSendThread.start()
        print("SingleSend Service Started. Monitoring directory is: ", settings["inputPath"])
    #FileAct Thread
    if settings["fileActService"]:
        print("Starting FileAct Service")
        fileActThread = threading.Thread(target=Watchdog.ThreadWatchdog, args=(settings["fileActInputPath"], FileInputCallback, stop_event))
        fileActThread.start()
        print("FileAct Service Started. Monitoring directory is: ", settings["fileActInputPath"])
    #Download Thread
    if settings["downloadService"]:
        print("Starting Download Service...")
        downloadThread=threading.Thread(target=Download.ThreadDownload, args=(settings, stop_event))
        downloadThread.start()
        print("Download Service Started.")
    #MessageMaker Thread
    if settings["messageMakerService"]:
        print("Starting MessageMaker Service...")
        messageMakerThread=threading.Thread(target=Watchdog.ThreadWatchdog, args=(settings["downloadPath"], MessageMakerCallback, stop_event))
        messageMakerThread.start()
        print("MessageMaker Service Started.")
    # Socket Listener Thread
    if settings.get("socketListenerService", False):
        print("Starting Socket Listener Service...")
        asyncSocketListener=Socket.AsyncSocketListener(settings)
        asyncSocketListenerThread=threading.Thread(target=asyncSocketListener.main)
        asyncSocketListenerThread.start()
        print("Socket Listener Service Started.")
    #Token Refresh Thread
    tokenRefreshThread=threading.Thread(target=Token.ThreadTokenRefresh, args=(settings, stop_event))
    tokenRefreshThread.start()
    
    while True:
        time.sleep(1)
        #asyncSocketListener.Send("10.10.3.100",12345,"asdasdasd.asdasdasd")
except KeyboardInterrupt:
    #Ctrl+C 입력 감지
    print("---------------------------------------------------------------")
    print("Stopping All Services...")
    print("---------------------------------------------------------------")
except Exception as e:
    print("---------------------------------------------------------------")
    print("Error:", type(e).__name__, e)
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
    """
    if settings["messageMakerService"]:
        print("Stopping MessageMaker Service...")
        stop_event.set()
        messageMakerThread.join(timeout=5)
        print("MessageMaker Service Stopped.")
    """
    if settings["socketListenerService"]:
        print("Stopping Socket Listener Service...")
        asyncSocketListener.stop()
        print("Socket Listener Service Stopped.")
    #Token Refresh Thread 종료
    stop_event.set()
    tokenRefreshThread.join(timeout=5)
    #사용중이던 토큰 폐기
    print("Revoking Access Token...")
    Token.RevokeToken(settings)
    print("Success")
    print("Program has terminated successfully")