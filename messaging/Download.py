import requests, json, time, base64
from messaging.Ack import *
from Token import GetAccessToken

    
def Download(accessToken, settings):
    with open(settings["distFile"], "r") as f:
        dist = json.load(f)
    dist=dist["distributions"]
    messages=[]
    reports=[]
    interactMessages=[]
    interactReports=[]
    fileactReports=[]
    fileactMessages=[]
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

    #print(f"{len(messages)} {len(reports)} {len(interactMessages)} {len(interactReports)}")
    reportUrl=settings["reportUrl"]
    messageUrl=settings["messageUrl"]
    interactReportUrl=settings["interActReportUrl"]
    interactMessageUrl=settings["interActMessageUrl"]
    fileactReportUrl=settings["fileActReportUrl"]
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

    #interact Ack 파일 Out
    if(len(interactReports) > 0):
        reportResponse=requests.get(interactReportUrl, headers=headers, params=mxreportParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        if(len(reportResponse) > 0):
            reportPath=f"{settings["downloadPath"]}/{int(time.time())}.mxreport"
            with open(reportPath, "w") as f:
                json.dump(reportResponse, f, indent=4)
            print("Download - MX Reports Downloaded")
            MultiAck(accessToken,interactReports,settings)  
    #FIN Ack 파일 Out
    if(len(reports) > 0):
        reportResponse=requests.get(reportUrl, headers=headers, params=reportParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        if(len(reportResponse) > 0):
            reportPath=f"{settings["downloadPath"]}/{int(time.time())}.report"
            with open(reportPath, "w") as f:
                json.dump(reportResponse, f, indent=4)
            print("Download - Reports Downloaded")
            MultiAck(accessToken,reports,settings)
    #interact message
    if(len(interactMessages) > 0):
        messageResponse=requests.get(interactMessageUrl, headers=headers, params=mxmessageParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        if(len(messageResponse) > 0):
            messagePath=f"{settings["downloadPath"]}/{int(time.time())}.mxmessage"
            with open(messagePath, "w") as f:
                json.dump(messageResponse, f, indent=4)
            print("Download - MX Messages Downloaded")
            MultiAck(accessToken,interactMessages,settings)
    #FIN 파일 out
    if(len(messages) > 0):
        messageResponse=requests.get(messageUrl, headers=headers, params=messageParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        if(len(messageResponse) > 0):
            messagePath=f"{settings["downloadPath"]}/{int(time.time())}.message"
            with open(messagePath, "w") as f:
                json.dump(messageResponse, f, indent=4)
            print("Download - Messages Downloaded")
            MultiAck(accessToken,messages,settings)
    #FileAct Report (Ack)
    if(len(fileactReports) > 0):
        reportResponse=requests.get(fileactReportUrl, headers=headers, params=filereportParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        if(len(reportResponse) > 0):
            reportPath=f"{settings["downloadPath"]}/{int(time.time())}.filereport"
            with open(reportPath, "w") as f:
                json.dump(reportResponse, f, indent=4)
            print("Download - File Reports Downloaded")
            MultiAck(accessToken,fileactReports,settings)

    #아무것도 없으면 그냥 넘어가기
    #print("Download - No Messages")


def ThreadDownload(settings, stopEvent):
    while not stopEvent.is_set():
        try:
            accessToken=GetAccessToken()
            distributionList = Download(accessToken, settings)
        except Exception as e:
            print("Download - ThreadDownload error:", type(e).__name__, e)
        for _ in range(int(settings["downloadInterval"])):
            if stopEvent.is_set():
                break
            time.sleep(1)


