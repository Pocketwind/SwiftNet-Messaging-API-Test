import time, json, os, tempfile, requests
import auth.Token as Token
import data.globalData as Data
import threading


class RetrieveService:
    def __init__(self, settings):
        self.settings = settings
        self.stop_event = threading.Event()
        self.thread = None

    def run_loop(self):
        while not self.stop_event.is_set():
            try:
                access_token = Data.GetAccessToken()
                distribution_list = Retrieve(access_token, self.settings)
                check = distribution_list.get("distributions")
                if not isinstance(check, dict):
                    print("Distribution - List Updated.")
                    Data.SetDistribution(distribution_list)
                    write_atomic(self.settings["distFile"], distribution_list)
                else:
                    print("Distribution - Token Expired. Need to Refresh")
            except Exception as e:
                print("ThreadRetrieve error:", type(e).__name__, e)
            for _ in range(int(self.settings["retrieveInterval"])):
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

#distributions - Retrieve the list of available distributions from Alliance Cloud.
#Ready to be distributed 인 메시지 리스트 불러오기
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
    response=requests.get(url, headers=headers, params=params, proxies=settings["proxies"], verify=True, timeout=5).json()
    return response

#파일로 읽고쓰기때문에 Deadlock 발생 -> 임시파일로 atomic하게 저장하면서 방지
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

#Retrieve 하는 스레드 정의
#실시간으로 업데이트 필요함 -> 스레드로 만들어서 대체
def ThreadRetrieve(settings, stopEvent):
    service = RetrieveService(settings)
    service.stop_event = stopEvent
    service.run_loop()