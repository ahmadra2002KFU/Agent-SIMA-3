"""
Upload hospital_patients.csv to the server
"""
import requests

url = "http://127.0.0.1:8010/upload"
files = {'file': open('hospital_patients.csv', 'rb')}

response = requests.post(url, files=files)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")