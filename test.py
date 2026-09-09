import requests

url = "https://ia-rt.onrender.com/api/v1/chat"
payload = {"message": "errore dgfe esurito"}

print("Invio della richiesta all'assistente cloud...")
response = requests.post(url, json=payload)

print(f"Status Code ricevuto: {response.status_code}")
print("Risposta ricevuta dal server:")
print(response.text)