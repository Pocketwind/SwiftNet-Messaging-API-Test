import dis

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

services=[]

try:
    accessToken = Auth.Auth(True, settings)
    Data.SetAccessToken(accessToken)

    #Distribution Thread
    if settings["distService"]:
        distributionService = Retrieve.RetrieveService(settings)
        services.append(distributionService)
    #SingleSend Thread
    if settings["singleSendService"]:
        singleSendService = SingleSend.SingleSendService(settings)
        services.append(singleSendService)
    #FileAct Thread
    if settings["fileActService"]:
        fileActService = FileAct.FileActService(settings)
        services.append(fileActService)
    #Download Thread
    if settings["downloadService"]:
        downloadService = Download.DownloadService(settings)
        services.append(downloadService)
    # Socket Listener Thread
    if settings.get("socketListenerService", False):
        asyncSocketListener = Socket.AsyncSocketListener(settings)
        services.append(asyncSocketListener)
    #MessageMaker Thread
    if settings["messageMakerService"]:
        messageMakerService = MessageMaker.MessageMakerService(settings, asyncSocketListener.send)
        services.append(messageMakerService)
    #Token Refresh Thread
    tokenRefreshService = Token.TokenRefreshService(settings)
    services.append(tokenRefreshService)
    
    #서비스 모두 시작
    for service in services:
        try:
            print(f"Starting {service.service_name} Service ...")
            service.start()
            print(f"{service.service_name} Service Started.")
        except Exception as e:
            print(f"Error: {service.service_name} Service 실행 중 오류 발생 - {e}")
            exit(1)
        
    
    while True:
        time.sleep(1)
        #asyncSocketListener.send("localhost",56788,"asdasdasd.asdasdasd")
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
    #서비스 모두 종료 stop
    for service in services:
        print(f"Stopping {service.service_name} Service...")
        service.stop()

    #서비스 모두 종료 join
    for service in services:
        service.join(timeout=5)
        print(f"{service.service_name} Service Stopped.")

    #사용중이던 토큰 폐기
    print("Revoking Access Token...")
    Token.RevokeToken(settings)
    print("Success")
    print("Program has terminated successfully")