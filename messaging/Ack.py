import requests, json, time, base64

proxies={
    "http":"http://10.10.3.101:48600",
    "https":"http://10.10.3.101:48600"
}

def SingleAck(accessToken, url, id):
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    param={
        "id":id
    }
    if url[:-4]!="acks":
        url=f"{url}/acks"
    print("Acknowledging URL:", url)
    response=requests.post(url, headers=headers, params=param, proxies=proxies, verify=False)
    print("Acked")

