import requests, json, time, base64

from Token import GetAccessToken

    
def Download(accessToken, settings):
    with open(settings["distFile"], "r") as f:
        dist = json.load(f)
    dist=dist["distributions"]
    messages=[]
    reports=[]
    for i in dist:
        if i["transmission_possible_duplicate"]:
            continue
        mtype=i.get("type")
        if mtype == "message":
            messages.append(i["id"])
        elif mtype == "transmissionReport":
            reports.append(i["id"])
    reportUrl="https://api-test.swiftnet.sipn.swift.com/alliancecloud-test/v2/fin/transmission-reports"
    messageUrl="https://api-test.swiftnet.sipn.swift.com/alliancecloud-test/v2/fin/messages"
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

    #메시지 파일 out
    if(len(messages) != 0):
        messageResponse=requests.get(messageUrl, headers=headers, params=messageParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        messagePath=f"{settings["downloadPath"]}/{int(time.time())}.message"
        with open(messagePath, "w") as f:
            json.dump(messageResponse, f, indent=4)
        print("Download - Messages Downloaded")
        for message in messages:
            SingleAck(accessToken, message, settings)
        return
    
    #Ack 파일 Out
    if(len(reports) != 0):
        reportResponse=requests.get(reportUrl, headers=headers, params=reportParam, proxies=settings["proxies"], verify=False, timeout=5).json()
        reportPath=f"{settings["downloadPath"]}/{int(time.time())}.report"
        with open(reportPath, "w") as f:
            json.dump(reportResponse, f, indent=4)
        print("Download - Reports Downloaded")
        for report in reports:
            SingleAck(accessToken, report, settings)

    #아무것도 없으면 그냥 넘어가기
    print("Download - No Messages")


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


def SingleAck(accessToken, id, settings):
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    param={
        "id":id
    }
    
    ackUrl="https://api-test.swiftnet.sipn.swift.com/alliancecloud-test/v2/distributions/<id>/acks"
    print("Download - Acknowledging ID:", id)
    ackUrl=ackUrl.replace("<id>",str(id))
    response=requests.post(ackUrl, headers=headers, params=param, proxies=settings["proxies"], verify=False)
    print(f"Download - Acked: {id}")