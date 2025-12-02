import requests

def Preval(url, accessToken, consumerCred):
    url=f"{url}/swift-preval/v3/accounts/verification"
    header={
        "Authorization":f"Bearer {accessToken}",
        "Content-Type":"application/json",
        "Accept":"application/json",
        "X-Request-ID":"550e8400-e29b-41d4-a716-446655440000",
        "X-Request-Date-Time":"2024-12-27T14:24:11.000Z"
    }
    body={
        "party_account":{
            "identification":{
                "iban":"GB12BANK34567890123456"
            }
        },
        "party_agent":{
            "bicfi":"CREDGB22XXX"
        },
        "requestor":{
            "any_bic":"REQTUS33XXX"
        },
        "context": "CRDT",
        "proprietary_service_parameters": {
            "code": "SCHM",
            "qualifier": "PVAH"
        }
    }
    response=requests.post(url, headers=header, json=body)
    return response.json()