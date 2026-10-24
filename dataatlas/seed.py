"""Load a deterministic example through the signed-in demo ingestion path."""
import json
import os
import urllib.request

def main():
    body=b"order_id,region,category,revenue,units\n1001,North,Books,42.50,2\n1002,South,Home,129.99,1\n1003,West,Books,18.00,1\n1004,North,Electronics,899.00,1\n1005,East,Home,64.25,3\n"
    base=f"http://{os.environ.get('DATAATLAS_HOST','127.0.0.1')}:{os.environ.get('DATAATLAS_PORT','8000')}"
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    auth=json.dumps({"username":"demo","password":os.environ.get("DATAATLAS_DEMO_PASSWORD","dataatlas-demo")}).encode()
    login=urllib.request.Request(base+"/api/auth/login",data=auth,headers={"Content-Type":"application/json"},method="POST")
    with opener.open(login) as response: response.read()
    boundary="----DataAtlasSeedBoundary"
    payload=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sample_orders.csv\"\r\nContent-Type: text/csv\r\n\r\n".encode()+body+f"\r\n--{boundary}--\r\n".encode())
    req=urllib.request.Request(base+"/api/ingest/csv",data=payload,headers={"Content-Type":f"multipart/form-data; boundary={boundary}","Idempotency-Key":"demo-sample-orders-v1"},method="POST")
    with opener.open(req) as response: print(response.read().decode())
if __name__=="__main__": main()
