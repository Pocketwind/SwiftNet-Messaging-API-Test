import requests

def GetBICDetails(url, accessToken, bic):
    accessUrl=f"{url}/swiftrefdata/v5/bics/{bic}"
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    response=requests.get(accessUrl, headers=headers).json()
    return response
    