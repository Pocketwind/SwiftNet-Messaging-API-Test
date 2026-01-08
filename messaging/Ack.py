import requests

#distributions - ACK a distribution
#실제로 메시지 파일을 다운로드 한 후 보내는 쿼리
#Distribution List에서 메시지 제거하는 역할 -> Complete 느낌
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
    response=requests.post(ackUrl, headers=headers, params=param, proxies=settings["proxies"], verify=True)
    print(f"Download - Acked: {id}")

#distributions - Update the status of multiple distributions in Alliance Cloud.
#SingleAck와 같지만 한번에 여러개 가능
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
    response=requests.patch(url,headers=headers,json=ackList,proxies=settings["proxies"],verify=True)
    print(f"Download - Acked {len(ids)}")

#MultiAck와 같지만 Nack 보내는 쿼리 -> 메시지 다운로드 중 오류(ex. 서버에 용량부족)
#Nack이기 때문에 Reason 같이 첨부 가능
def MultiNak(accessToken, ids, reason, settings):
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    nackList=[]
    for id in ids:
        nackList.append({
            "id":id,
            "status":"Nak",
            "status_update_message":reason
        })
    url=settings["distUrl"]
    response=requests.patch(url,headers=headers,json=nackList,proxies=settings["proxies"],verify=True)
    print(f"Download - Nacked {len(ids)}")