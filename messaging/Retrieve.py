import requests, time, json, os, tempfile
from Token import *


def Retrieve(accessToken, settings):
    url=settings["distUrl"]
    headers={
        "Accept":"application/json",
        "Authorization":f"Bearer {accessToken}"
    }
    params={
        "limit":settings["maxDistSize"],
        "offset":0
    }
    response=requests.get(url, headers=headers, params=params, proxies=settings["proxies"], verify=False).json()
    return response

def write_atomic(path, data):
    dirpath = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".tmp_distlist_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tf:
            json.dump(data, tf, ensure_ascii=False, separators=(',', ':'), indent=4)
            tf.flush()
            os.fsync(tf.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise

def ThreadRetrieve(settings, stopEvent):
    while not stopEvent.is_set():
        try:
            accessToken=GetAccessToken()
            distributionList = Retrieve(accessToken, settings)
            check=distributionList.get("distributions")
            if not isinstance(check, dict):
                print("Distribution - List Updated.")
                write_atomic(settings["distFile"], distributionList)
            else:
                print("Distribution - Token Expired. Need to Refresh")
        except Exception as e:
            print("ThreadRetrieve error:", type(e).__name__, e)
        for _ in range(int(settings["retrieveInterval"])):
            if stopEvent.is_set():
                break
            time.sleep(1)