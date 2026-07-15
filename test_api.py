import requests

url = "http://127.0.0.1:8000/api/agriino/devices/daily_averages/"
try:
    res = requests.get(url)
    print("Status code:", res.status_code)
    data = res.json()
    print(f"Total days of history returned: {len(data)}")
    for day in data[:10]:
        print(f"Date: {day['date']}, Label: {day['dateLabel']}, Nitrogen Avg: {day['avgNitrogen']:.4f}, Readings Count: {day['readingsCount']}")
except Exception as e:
    print("Error calling endpoint:", e)
