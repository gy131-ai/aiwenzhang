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

def parse_link(value):
    if isinstance(value, dict):
        return value.get('link', value.get('url', value.get('text', str(value))))
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                link = item.get('link', item.get('url', ''))
                if link:
                    return link
        return ''
    return str(value) if value else ""

def parse_richtext(content):
    if isinstance(content, list):
        result = ""
        for item in content:
            if isinstance(item, dict):
                if 'text' in item:
                    result += item['text']
                elif 'type' in item and item['type'] == 'image' and 'image_key' in item:
                    image_key = item['image_key']
                    result += f'<img src="/image/{image_key}" style="max-width: 100%; height: auto; border-radius: 12px; margin: 15px 0;" />'
                elif 'type' in item and item['type'] == 'paragraph':
                    result += '\n'
            elif isinstance(item, str):
                result += item
        return result
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
                if key == '链接':
                    fields[key] = parse_link(value)
                else:
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

@app.route('/image/<image_key>')
def serve_image(image_key):
    token = get_feishu_token()
    if not token:
        return "获取token失败", 500
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app.config['BASE_ID']}/images/{image_key}/raw"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, stream=True)
    
    if response.status_code == 200:
        return response.content, response.status_code, {'Content-Type': response.headers.get('Content-Type', 'image/jpeg')}
    return "图片获取失败", 404

@app.route('/refresh')
def refresh():
    global cached_data
    cached_data = None
    return "数据已刷新"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')