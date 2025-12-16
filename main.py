import Authorization as auth
from messaging.Retrieve import *
from messaging.Download import *
from messaging.SingleSend import *
from messaging.FileAct import *
from messaging.Watchdog import *
from messaging.MessageMaker import *
import json, threading, time, os, warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


with open("settings.json","r") as f:
    settings=json.load(f)


def MessageInputCallback(path):
    MessageCollector(path, settings)
def MessageMakerCallback(downloadPath):
    MessageMaker(downloadPath, settings["outputPath"], settings["ackPath"])
def FileInputCallback(path):
    FileCollector(path, settings)


try:
    accessToken = auth.Auth(True, settings)
    stop_event = threading.Event()
    #Initialize Threads
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
        accessToken = auth.Auth(True, settings)
        SetAccessToken(accessToken)
        time.sleep(settings["expirationTime"])

except KeyboardInterrupt:
    print("---------------------------------------------------------------")
    print("Stopping All Services...")
    print("---------------------------------------------------------------")
finally:
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
    print("---------------------------------------------------------------")
    print("Revoking Access Token...")
    RevokeToken(settings)
    print("Success")    
    print("---------------------------------------------------------------")
    print("Program has terminated successfully")