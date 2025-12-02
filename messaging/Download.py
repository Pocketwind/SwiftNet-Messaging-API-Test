import requests, json, time, base64

from Token import GetAccessToken

proxies={
    "http":"http://10.10.3.101:48600",
    "https":"http://10.10.3.101:48600"
}

    
def Download(accessToken, distPath, downloadPath):
    with open(distPath, "r") as f:
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

    if(len(messages) != 0):
        messageResponse=requests.get(messageUrl, headers=headers, params=messageParam, proxies=proxies, verify=False, timeout=5).json()
        messagePath=f"{downloadPath}/{int(time.time())}.message"
        with open(messagePath, "w") as f:
            json.dump(messageResponse, f, indent=4)
        print("Messages Downloaded")
        for message in messages:
            SingleAck(accessToken, message)
    elif(len(reports) != 0):
        reportResponse=requests.get(reportUrl, headers=headers, params=reportParam, proxies=proxies, verify=False, timeout=5).json()
        reportPath=f"{downloadPath}/{int(time.time())}.report"
        with open(reportPath, "w") as f:
            json.dump(reportResponse, f, indent=4)
        print("Reports Downloaded")
        for report in reports:
            SingleAck(accessToken, report)
    else:
        print("No Messages")


def ThreadDownload(downloadPath, distPath, GetAccessToken, interval, stopEvent):
    while not stopEvent.is_set():
        try:
            accessToken=GetAccessToken()
            distributionList = Download(accessToken, distPath, downloadPath)
        except Exception as e:
            print("ThreadDownload error:", type(e).__name__, e)
        for _ in range(int(interval)):
            if stopEvent.is_set():
                break
            time.sleep(1)


def SingleAck(accessToken, id):
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    param={
        "id":id
    }
    
    ackUrl="https://api-test.swiftnet.sipn.swift.com/alliancecloud-test/v2/distributions/<id>/acks"
    print("Acknowledging ID:", id)
    ackUrl=ackUrl.replace("<id>",str(id))
    response=requests.post(ackUrl, headers=headers, params=param, proxies=proxies, verify=False)
    print(f"Acked: {id}")