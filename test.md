import requests
  
url = "https://scraper-api.decodo.com/v2/scrape"
  
payload = {
      "target": "chatgpt",
      "prompt": "What are the top three dog breeds?",
      "search": True,
      "geo": "India",
      "markdown": True
}
  
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Basic VTAwMDAzMzY2NTk6UFdfMWM5ZjBkMjg3NjM2NDIwYjAxNDZiNTUxYTcyMDI5NWFk"
}
  
response = requests.post(url, json=payload, headers=headers)
  
print(response.text)