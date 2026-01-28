"""Test Gemini's ability to analyze multiple ECG images"""
import os
import base64
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from pathlib import Path
from api.ai_service import parse_document_to_records

ECG_BASE = Path(r"C:\Users\Lenovo\Desktop\dyp\oop cp\Cardiovascular-Detection-using-ECG-images\ECG_IMAGES_DATASET")
NORMAL_DIR = ECG_BASE / "Normal Person ECG Images (284x12=3408)"
MI_DIR = ECG_BASE / "ECG Images of Myocardial Infarction Patients (240x12=2880)"

def test_single(img_path):
    with open(img_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    
    docs = [{'type': 'image', 'name': img_path.name, 'mime_type': 'image/jpeg', 'data': data}]
    result = parse_document_to_records(docs, '')
    
    for r in result.get('records', []):
        status = r.get('status', 'unknown')
        title = r.get('title', 'Unknown')
        summary = r.get('summary', '')[:100]
        return status, title, summary
    return 'no_record', 'N/A', 'N/A'

print("Testing Normal ECGs with Gemini:")
print("-" * 60)
normal_files = sorted([f for f in os.listdir(NORMAL_DIR) if f.endswith('.jpg')])[:5]
for f in normal_files:
    img = NORMAL_DIR / f
    status, title, summary = test_single(img)
    print(f"{f}: {status} - {summary[:60]}...")

print("\nTesting MI ECGs with Gemini:")
print("-" * 60)
mi_files = sorted([f for f in os.listdir(MI_DIR) if f.endswith('.jpg')])[:5]
for f in mi_files:
    img = MI_DIR / f
    status, title, summary = test_single(img)
    print(f"{f}: {status} - {summary[:60]}...")
