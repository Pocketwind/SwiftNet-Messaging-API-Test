import Authorization as auth
from BIC_Details import *
from Preval import *
from messaging.Retrieve import *
from messaging.Download import *
from messaging.SingleSend import *
from messaging.Watchdog import *
from messaging.MessageMaker import *
import json, threading, time, os, warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


with open("settings.json","r") as f:
    settings=json.load(f)


def MessageInputCallback(path):
    print("---------------------------------------------------------------")
    with open(path, 'r') as f:
        data=f.read()
        messageData=MTParser(data)
        #response = SingleSend(accessToken, messageData)
        response = SingleSend(messageData, settings)
    os.remove(path)
    print(f'File {path} is processed and removed.')
    print("---------------------------------------------------------------")
    print()
def MessageMakerCallback(downloadPath):
    MessageMaker(downloadPath, settings["outputPath"], settings["ackPath"])


try:
    accessToken = auth.Auth(True, settings["jwtConfig"])
    #Initialize Threads
    #SingleSend Thread
    stop_event = threading.Event()
    print("Starting SingleSend Thread...")
    singleSendThread = threading.Thread(target=ThreadSingleSend, args=(settings["inputPath"], MessageInputCallback, stop_event))
    singleSendThread.start()
    print("SingleSend Thread Started. Monitoring directory is:", settings["inputPath"])
    #Distribution Thread
    print("Starting Distribution List Retrieval Loop...")
    distributionThread = threading.Thread(target=ThreadRetrieve, args=(settings, stop_event))
    distributionThread.start()
    print("Distribution List Retrieval Loop Started.")
    #Download Thread
    print("Starting Download Thread...")
    downloadThread=threading.Thread(target=ThreadDownload, args=(settings, stop_event))
    downloadThread.start()
    print("Download Thread Started.")
    #MessageMaker Thread
    print("Starting MessageMaker Thread...")
    messageMakerThread=threading.Thread(target=ThreadMessageMaker, args=(settings, MessageMakerCallback, stop_event))
    messageMakerThread.start()
    print("MessageMaker Thread Started.")
    print("---------------------------------------------------------------")
    #Wait
    time.sleep(3)
    while True:
        #Main Thread
        #Auth Check
        accessToken = auth.Auth(True, settings["jwtConfig"])
        SetAccessToken(accessToken)
        time.sleep(settings["jwtConfig"]["expirationTime"])

except KeyboardInterrupt:
    print("---------------------------------------------------------------")
    print("Stopping All Services...")
    print("---------------------------------------------------------------")
finally:
    print("Stopping SingleSend Thread...")
    stop_event.set()            
    singleSendThread.join(timeout=5) 
    print("SingleSend Thread Stopped.")
    print("Stopping Distribution Thread...")
    stop_event.set()            
    distributionThread.join(timeout=5)
    print("Distribution Thread Stopped.")
    print("Stopping Download Thread...")
    stop_event.set()
    downloadThread.join(timeout=5)
    print("Download Thread Stopped.")
    print("Stopping MessageMaker Thread...")
    stop_event.set()
    messageMakerThread.join(timeout=5)
    print("MessageMaker Thread Stopped.")

    