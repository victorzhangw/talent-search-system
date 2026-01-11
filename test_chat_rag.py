import requests
import json

url = 'http://127.0.0.1:5000/chat'
headers = {'Content-Type': 'application/json'}
payload = {
    "query": "請分析這位候選人的性格特質",
    "candidate_ids": ["cand_001"],
    "session_id": "test_sess_001"
}

try:
    print(f"Sending request to {url}...")
    with requests.post(url, json=payload, headers=headers, stream=True) as r:
        print(f"Status Code: {r.status_code}")
        if r.status_code != 200:
            print("Error Response:", r.text)
        else:
            print("Streaming Response:")
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_str = decoded_line[6:]
                        try:
                            # Parse JSON if possible, otherwise print raw
                            data_json = json.loads(data_str)
                            # We are looking for the 'token' type which contains the text
                            # But since we want to see the CONTEXT (which isn't returned to client usually, but used in prompt)
                            # We can only infer from the answer.
                            # However, if I want to debug the context, I should have printed it in `rag_engine.py` or logged it.
                            # For now, let's see what the LLM says. If it mentions "情境式盡責" or "B Band", then it works.
                            if data_json.get('type') == 'token':
                                print(data_json['content'], end='', flush=True)
                            elif data_json.get('type') == 'error':
                                print("\nERROR:", data_json['content'])
                        except:
                            print(decoded_line)
            print("\nDone.")
except Exception as e:
    print(f"Request Failed: {e}")
