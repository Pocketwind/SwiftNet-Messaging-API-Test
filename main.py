import Authorization as auth
from BIC_Details import *
from Preval import *
from messaging import Ack
from messaging.Retrieve import *
from messaging.Download import *
from messaging.SingleSend import *
from messaging.Watchdog import *
from messaging.MessageMaker import *
from messaging.Ack import *
import json, threading, time, os, warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

BASE_URL="https://sandbox.swift.com"
INPUT_PATH="D:/AFT/in"
OUTPUT_PATH="D:/AFT/out"
DOWNLOAD_PATH="D:/AFT/download"
ACK_PATH="D:/AFT/ack"
DIST_PATH="distList.json"
RETRIEVE_INTERVAL=30
DOWNLOAD_INTERVAL=40

"""
#------------------Basic Auth Example------------------
accessToken, consumerCred = auth.Auth(False)
response = GetBICDetails(BASE_URL, accessToken, "CJCCKRSS")
print(response)
"""

#------------------JWT Auth Example--------------------
"""accessToken, consumerCred = auth.Auth(True)
print("Access Token:", accessToken)"""

def MessageInputCallback(path):
    print("---------------------------------------------------------------")
    with open(path, 'r') as f:
        data=f.read()
        """print("Original Message:")
        print(data)
        print()"""
        messageData=MTParser(data)
        """print("Parsed Message Data:")
        print("TRN:", messageData['trn'])
        print("FIN Type:", messageData['finType'])
        print("Sender:", messageData['sender'])
        print("Receiver:", messageData['receiver'])
        print("Payload:")
        print(messageData['payload'])
        print()
        print("Sending a Message...")"""
        #response = SingleSend(accessToken, messageData)
        response = SingleSend(GetAccessToken, messageData)
        """print("Single Send Response:", response)"""
    os.remove(path)
    print(f'File {path} is processed and removed.')
    print("---------------------------------------------------------------")
    print()
def MessageMakerCallback(downloadPath):
    MessageMaker(downloadPath, OUTPUT_PATH, ACK_PATH)


try:
    #Set Access Token
    accessToken, consumerCred = auth.Auth(True)
    SetAccessToken(accessToken)
    #Initialize Threads
    #SingleSend Thread
    stop_event = threading.Event()
    print("Starting SingleSend Thread...")
    singleSendThread = threading.Thread(target=ThreadSingleSend, args=(INPUT_PATH, MessageInputCallback, stop_event))
    singleSendThread.start()
    print("SingleSend Thread Started. Monitoring directory is:", INPUT_PATH)
    #Distribution Thread
    print("Starting Distribution List Retrieval Loop...")
    #distributionThread = threading.Thread(target=ThreadRetrieve, args=(DIST_PATH, accessToken, 200, 30, stop_event))
    distributionThread = threading.Thread(target=ThreadRetrieve, args=(DIST_PATH, GetAccessToken, 200, RETRIEVE_INTERVAL, stop_event))
    distributionThread.start()
    print("Distribution List Retrieval Loop Started.")
    #Download Thread
    print("Starting Download Thread...")
    #downloadThread=threading.Thread(target=ThreadDownload, args=(DOWNLOAD_PATH,DIST_PATH,accessToken, 20, stop_event))
    downloadThread=threading.Thread(target=ThreadDownload, args=(DOWNLOAD_PATH,DIST_PATH,GetAccessToken, DOWNLOAD_INTERVAL, stop_event))
    downloadThread.start()
    print("Download Thread Started.")
    #MessageMaker Thread
    print("Starting MessageMaker Thread...")
    messageMakerThread=threading.Thread(target=ThreadMessageMaker, args=(DOWNLOAD_PATH, MessageMakerCallback, stop_event))
    messageMakerThread.start()
    print("MessageMaker Thread Started.")
    print("---------------------------------------------------------------")
    #Wait
    time.sleep(3)
    while True:
        #Main Thread
        #Auth Check
        accessToken, consumerCred = auth.Auth(True)
        SetAccessToken(accessToken)
        time.sleep(60*10)

except Exception as e:
    print(e)
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