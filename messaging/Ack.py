import requests, json, time, base64

def SingleAck(accessToken, id, settings):
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    param={
        "id":id
    }
    
    ackUrl=settings["ackUrl"]
    print("Download - Acknowledging ID:", id)
    ackUrl=ackUrl.replace("<id>",str(id))
    response=requests.post(ackUrl, headers=headers, params=param, proxies=settings["proxies"], verify=False)
    print(f"Download - Acked: {id}")

def MultiAck(accessToken, ids, settings):
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    ackList=[]
    for id in ids:
        ackList.append({
            "id":id,
            "status":"Ack"
        })
    url=settings["distUrl"]
    response=requests.patch(url,headers=headers,json=ackList,proxies=settings["proxies"],verify=False)
    print(f"Download - Acked {len(ids)}")