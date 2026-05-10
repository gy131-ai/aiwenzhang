from flask import Flask, render_template
import requests
import json

app = Flask(__name__)
app.config.from_object('config.Config')

cached_data = None
cache_time = 0

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": app.config['FEISHU_APP_ID'],
        "app_secret": app.config['FEISHU_APP_SECRET']
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("tenant_access_token")
    return None

def parse_richtext(content):
    if isinstance(content, list):
        text = ""
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                text += item['text']
            elif isinstance(item, str):
                text += item
        return text
    return str(content) if content else ""

def fetch_records():
    token = get_feishu_token()
    if not token:
        return []
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app.config['BASE_ID']}/tables/{app.config['TABLE_ID']}/records"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("data", {}).get("items", [])
        for item in items:
            fields = item.get("fields", {})
            for key, value in fields.items():
                fields[key] = parse_richtext(value)
        return items
    return []

def get_records():
    global cached_data
    if cached_data is None:
        cached_data = fetch_records()
    return cached_data

def get_record_by_id(record_id):
    records = get_records()
    for record in records:
        if record.get("record_id") == record_id:
            return record
    return None

@app.route('/')
def index():
    records = get_records()
    return render_template('index.html', articles=records)

@app.route('/article/<record_id>')
def article_detail(record_id):
    record = get_record_by_id(record_id)
    if not record:
        return "文章未找到", 404
    return render_template('detail.html', article=record)

@app.route('/refresh')
def refresh():
    global cached_data
    cached_data = None
    return "数据已刷新"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')