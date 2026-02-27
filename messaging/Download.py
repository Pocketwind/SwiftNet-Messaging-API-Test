import requests, json, time, threading
import data.globalData as Data
import messaging.Ack as Ack


class DownloadService:
    def __init__(self, settings):
        self.settings = settings
        self.thread = None
        self.stop_event = threading.Event()

    def run_loop(self):
        time.sleep(5)
        while not self.stop_event.is_set():
            try:
                access_token = Data.GetAccessToken()
                Download(access_token, self.settings)
            except Exception as e:
                print("Download - ThreadDownload error:", type(e).__name__, e)
            for _ in range(int(self.settings["downloadInterval"])):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.run_loop)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def join(self, timeout=5):
        if self.thread:
            self.thread.join(timeout=timeout)

#Download one or several FIN, Interact, FileAct messages ready to be distributed.
#Distribution List 에서 다운로드가 필요한 메시지 파일 검사 후 다운로드
def Download(accessToken, settings):
    #1. Distribution List 읽어오기
    """
    try:
        with open(settings["distFile"], "r") as f:
            dist = json.load(f)
        dist=dist["distributions"]
    except FileNotFoundError:
        print(f"\nFile {settings["distFile"]} not found.\nNeed to be updated later\n\n")
        return 
    """
    try:
        dist=Data.GetDistribution()["distributions"]
    except:
        return


    #2. 메시지 ID 저장할 배열
    messages=[]
    reports=[]
    interactMessages=[]
    interactReports=[]
    fileactReports=[]
    fileactMessages=[]

    #3. 메시지 다운로드 요청을 시도하면 transmission_possible_duplicate 값이 true로 변경
    #현재 구현 방식에서는 false인 값 (한번도 다운로드를 요청하지 않은) 메시지들의 ID만 추출해서 다운로드 요청함
    #필드 값들로 필터링
    for i in dist:
        if i["transmission_possible_duplicate"]:
            continue
        mtype=i.get("type")
        mservice=i.get("service")
        if mtype == "message" and mservice == "fin":
            messages.append(i["id"])
        elif mtype == "transmissionReport" and mservice == "fin":
            reports.append(i["id"])
        elif mtype == "message" and mservice == "interAct":
            interactMessages.append(i["id"])
        elif mtype == "transmissionReport" and mservice == "interAct":
            interactReports.append(i["id"])
        elif mtype == "transmissionReport" and mservice == "fileAct":
            fileactReports.append(i["id"])

    #4. 쿼리 요청할 URL들 settings에서 불러오기
    reportUrl=settings["reportUrl"]
    messageUrl=settings["messageUrl"]
    interactReportUrl=settings["interActReportUrl"]
    interactMessageUrl=settings["interActMessageUrl"]
    fileactReportUrl=settings["fileActReportUrl"]

    #5. 쿼리 헤더와 파라미터 설정
    #각 쿼리마다 distribution-id 값을 넣어주어야 하고 ',' 로 id들을 이어붙여야함 -> 한번에 여러개 요청 가능
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    messageParam={
        "distribution-id":",".join(str(i) for i in messages)
    }
    reportParam={
        "distribution-id":",".join(str(i) for i in reports)
    }
    mxmessageParam={
        "distribution-id":",".join(str(i) for i in interactMessages)
    }
    mxreportParam={
        "distribution-id":",".join(str(i) for i in interactReports)
    }
    filereportParam={
        "distribution-id":",".join(str(i) for i in fileactReports)
    }

    #6. 메시지 파일 다운로드 파트
    #실제 메시지가 오는것이 아닌 전체적인 정보와 함께 반환
    #B.O. 와 File Transfer 연계 시에 협의 후 실제 MT/MX로 변환해야 할지, 그대로 전달할지 협의가 필요해 보임
    #변환 시 장점 - Access 사용하던 자리에 그대로 대치 가능
    #직접 전달 시 장점 - B.O. 개발자와 Messaging API 개발자들에게 메시지 파싱할 파트가 사라지니 서로 좋을것으로 보임
    #다운로드 한 파일은 아카이브 목적으로 사용 가능할수도
    #interact Ack 파일 Out
    if(len(interactReports) > 0):
        reportResponse=requests.get(interactReportUrl, headers=headers, params=mxreportParam, proxies=settings["proxies"], verify=True, timeout=5).json()
        if(len(reportResponse) > 0):
            reportPath=f"{settings["downloadPath"]}/{int(time.time())}.mxreport"
            with open(reportPath, "w") as f:
                json.dump(reportResponse, f, indent=4)
            print("Download - MX Reports Downloaded")
            Ack.MultiAck(accessToken,interactReports,settings)  
    #FIN Ack 파일 Out
    if(len(reports) > 0):
        reportResponse=requests.get(reportUrl, headers=headers, params=reportParam, proxies=settings["proxies"], verify=True, timeout=5).json()
        if(len(reportResponse) > 0):
            reportPath=f"{settings["downloadPath"]}/{int(time.time())}.report"
            with open(reportPath, "w") as f:
                json.dump(reportResponse, f, indent=4)
            print("Download - Reports Downloaded")
            Ack.MultiAck(accessToken,reports,settings)
    #interact message
    if(len(interactMessages) > 0):
        messageResponse=requests.get(interactMessageUrl, headers=headers, params=mxmessageParam, proxies=settings["proxies"], verify=True, timeout=5).json()
        if(len(messageResponse) > 0):
            messagePath=f"{settings["downloadPath"]}/{int(time.time())}.mxmessage"
            with open(messagePath, "w") as f:
                json.dump(messageResponse, f, indent=4)
            print("Download - MX Messages Downloaded")
            Ack.MultiAck(accessToken,interactMessages,settings)
    #FIN 파일 out
    if(len(messages) > 0):
        messageResponse=requests.get(messageUrl, headers=headers, params=messageParam, proxies=settings["proxies"], verify=True, timeout=5).json()
        if(len(messageResponse) > 0):
            messagePath=f"{settings["downloadPath"]}/{int(time.time())}.message"
            with open(messagePath, "w") as f:
                json.dump(messageResponse, f, indent=4)
            print("Download - Messages Downloaded")
            Ack.MultiAck(accessToken,messages,settings)
    #FileAct Report (Ack)
    if(len(fileactReports) > 0):
        reportResponse=requests.get(fileactReportUrl, headers=headers, params=filereportParam, proxies=settings["proxies"], verify=True, timeout=5).json()
        if(len(reportResponse) > 0):
            reportPath=f"{settings["downloadPath"]}/{int(time.time())}.filereport"
            with open(reportPath, "w") as f:
                json.dump(reportResponse, f, indent=4)
            print("Download - File Reports Downloaded")
            Ack.MultiAck(accessToken,fileactReports,settings)

    #아무것도 없으면 그냥 넘어가기
    #print("Download - No Messages")

#다운로드 관리하는 스레드
def ThreadDownload(settings, stopEvent):
    service = DownloadService(settings)
    service.stop_event = stopEvent
    service.run_loop()


