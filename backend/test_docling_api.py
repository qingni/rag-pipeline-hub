#!/usr/bin/env python3
import base64
import httpx

# 读取测试 PDF
with open('uploads/billionaires_page-1-5.pdf', 'rb') as f:
    content = base64.b64encode(f.read()).decode('utf-8')

# 构建请求
request_body = {
    'options': {
        'to_formats': ['md'],
        'do_ocr': True,
        'table_mode': 'accurate',
        'abort_on_error': False
    },
    'sources': [
        {
            'kind': 'file',
            'base64_string': content,
            'filename': 'test.pdf'
        }
    ]
}

print('Sending request to Docling Serve...')
try:
    with httpx.Client(timeout=60) as client:
        response = client.post('http://localhost:5001/v1/convert/source', json=request_body)
        print(f'Status: {response.status_code}')
        if response.status_code != 200:
            print(f'Error: {response.text[:1000]}')
        else:
            print('Success!')
            data = response.json()
            docs = data.get("documents", [])
            print(f'Documents: {len(docs)}')
            if docs:
                print(f'Keys: {docs[0].keys()}')
except Exception as e:
    print(f'Exception: {e}')
