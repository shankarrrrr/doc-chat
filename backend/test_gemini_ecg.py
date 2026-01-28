"""Test Gemini's ability to analyze ECG images"""
import os
import sys
import base64

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from pathlib import Path
from api.ai_service import parse_document_to_records

ECG_DATASET = Path(r"C:\Users\Lenovo\Desktop\dyp\oop cp\Cardiovascular-Detection-using-ECG-images\ECG_IMAGES_DATASET")
NORMAL_DIR = ECG_DATASET / "Normal Person ECG Images (284x12=3408)"
MI_DIR = ECG_DATASET / "ECG Images of Myocardial Infarction Patients (240x12=2880)"

def test_ecg_with_gemini(image_path, description):
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Image: {image_path.name}")
    print('='*60)
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    documents = [{
        'type': 'image',
        'name': image_path.name,
        'mime_type': 'image/jpeg',
        'data': image_data
    }]
    
    try:
        result = parse_document_to_records(documents, '')
        
        print("\nRecords found:")
        for record in result.get('records', []):
            print(f"\n  Category: {record.get('category')}")
            print(f"  Title: {record.get('title')}")
            print(f"  Status: {record.get('status')}")
            print(f"  Summary: {record.get('summary', '')[:200]}...")
            if record.get('details'):
                print(f"  Details: {record.get('details')}")
        
        if result.get('health_summary'):
            print(f"\nHealth Summary: {result['health_summary'][:300]}...")
            
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == '__main__':
    # Test Normal ECG
    normal_img = NORMAL_DIR / "Normal(1).jpg"
    if normal_img.exists():
        test_ecg_with_gemini(normal_img, "Normal ECG")
    
    # Test MI ECG
    mi_img = MI_DIR / "MI(1).jpg"
    if mi_img.exists():
        test_ecg_with_gemini(mi_img, "Myocardial Infarction ECG")
    
    print("\n" + "="*60)
    print("Test completed!")
