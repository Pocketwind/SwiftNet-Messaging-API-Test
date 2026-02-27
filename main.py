import pip_system_certs.wrapt_requests
pip_system_certs.wrapt_requests.inject_truststore()
import auth.Authorization as Auth
import auth.Token as Token
import auth.HSM as HSM
import messaging.Retrieve as Retrieve
import messaging.Download as Download
import messaging.SingleSend as SingleSend
import messaging.FileAct as FileAct
import messaging.MessageMaker as MessageMaker
import messaging.SocketListener as Socket
import data.globalData as Data
import json, time, os, warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

#Settings 읽어오기
with open("settings.json","r") as f:
    settings=json.load(f)

#HSM 사용여부 확인
use_hsm=settings.get("useHSM", False)
if use_hsm:
    hsm_id=settings.get("hsmID", None)
    Data.SetCertificate(HSM.get_cert_pem(hsm_id))
else:
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

try:
    accessToken = Auth.Auth(True, settings)
    Data.SetAccessToken(accessToken)
    distributionService = None
    singleSendService = None
    fileActService = None
    downloadService = None
    messageMakerService = None
    tokenRefreshService = None
    asyncSocketListener = None

    #Distribution Thread
    if settings["distService"]:
        print("Starting Distribution Service...")
        distributionService = Retrieve.RetrieveService(settings)
        distributionService.start()
        print("Distribution Service Started.")
    #SingleSend Thread
    if settings["singleSendService"]:
        print("Starting SingleSend Service...")
        singleSendService = SingleSend.SingleSendService(settings)
        singleSendService.start()
        print("SingleSend Service Started. Monitoring directory is: ", settings["inputPath"])
    #FileAct Thread
    if settings["fileActService"]:
        print("Starting FileAct Service")
        fileActService = FileAct.FileActService(settings)
        fileActService.start()
        print("FileAct Service Started. Monitoring directory is: ", settings["fileActInputPath"])
    #Download Thread
    if settings["downloadService"]:
        print("Starting Download Service...")
        downloadService = Download.DownloadService(settings)
        downloadService.start()
        print("Download Service Started.")
    # Socket Listener Thread
    if settings.get("socketListenerService", False):
        print("Starting Socket Listener Service...")
        asyncSocketListener=Socket.AsyncSocketListener(settings)
        asyncSocketListener.start()
        print("Socket Listener Service Started.")
    #MessageMaker Thread
    if settings["messageMakerService"]:
        if asyncSocketListener is None:
            raise RuntimeError("messageMakerService requires socketListenerService")
        print("Starting MessageMaker Service...")
        messageMakerService = MessageMaker.MessageMakerService(settings, asyncSocketListener.send)
        messageMakerService.start()
        print("MessageMaker Service Started.")
    #Token Refresh Thread
    tokenRefreshService = Token.TokenRefreshService(settings)
    tokenRefreshService.start()
    
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
    print("---------------------------------------------------------------")
finally:
    #서비스(스레드) 모두 종료 - 1) stop 전체 호출
    if settings.get("singleSendService", False):
        print("Stopping SingleSend Service...")
        if singleSendService is not None:
            singleSendService.stop()
    if settings.get("fileActService", False):
        print("Stopping FileAct Service...")
        if fileActService is not None:
            fileActService.stop()
    if settings.get("distService", False):
        print("Stopping Distribution Service...")
        if distributionService is not None:
            distributionService.stop()
    if settings.get("downloadService", False):
        print("Stopping Download Service...")
        if downloadService is not None:
            downloadService.stop()
    if settings.get("messageMakerService", False):
        print("Stopping MessageMaker Service...")
        if messageMakerService is not None:
            messageMakerService.stop()
    if settings.get("socketListenerService", False):
        print("Stopping Socket Listener Service...")
        if asyncSocketListener is not None:
            asyncSocketListener.stop()
    if tokenRefreshService is not None:
        tokenRefreshService.stop()

    #서비스(스레드) 모두 종료 - 2) join 전체 대기
    if settings.get("singleSendService", False) and singleSendService is not None:
        singleSendService.join(timeout=5)
        print("SingleSend Service Stopped.")
    if settings.get("fileActService", False) and fileActService is not None:
        fileActService.join(timeout=5)
        print("FileAct Service Stopped.")
    if settings.get("distService", False) and distributionService is not None:
        distributionService.join(timeout=5)
        print("Distribution Service Stopped.")
    if settings.get("downloadService", False) and downloadService is not None:
        downloadService.join(timeout=5)
        print("Download Service Stopped.")
    if settings.get("messageMakerService", False) and messageMakerService is not None:
        messageMakerService.join(timeout=5)
        print("MessageMaker Service Stopped.")
    if settings.get("socketListenerService", False) and asyncSocketListener is not None:
        asyncSocketListener.join(timeout=5)
        print("Socket Listener Service Stopped.")
    if tokenRefreshService is not None:
        tokenRefreshService.join(timeout=5)
    #사용중이던 토큰 폐기
    print("Revoking Access Token...")
    Token.RevokeToken(settings)
    print("Success")
    print("Program has terminated successfully")