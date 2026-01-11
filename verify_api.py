import requests

try:
    resp = requests.get('http://127.0.0.1:5000/health')
    print(f"Status: {resp.status_code}")
    print("Body:")
    print(resp.text)
except Exception as e:
    print(e)
