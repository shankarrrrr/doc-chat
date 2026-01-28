"""Extended ECG accuracy test"""
import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from api.ecg_service import ECGPredictor
from pathlib import Path

ECG_BASE = Path(r"C:\Users\Lenovo\Desktop\dyp\oop cp\Cardiovascular-Detection-using-ECG-images\ECG_IMAGES_DATASET")
NORMAL_DIR = ECG_BASE / "Normal Person ECG Images (284x12=3408)"
MI_DIR = ECG_BASE / "ECG Images of Myocardial Infarction Patients (240x12=2880)"

predictor = ECGPredictor()

# Get actual files
normal_files = sorted([f for f in os.listdir(NORMAL_DIR) if f.endswith('.jpg')])[:30]
mi_files = sorted([f for f in os.listdir(MI_DIR) if f.endswith('.jpg')])[:30]

print("Testing 30 Normal ECGs...")
correct_normal = 0
total_normal = 0
for f in normal_files:
    img = NORMAL_DIR / f
    r = predictor.predict_from_ecg_image(str(img))
    if r['success']:
        total_normal += 1
        if r['prediction_code'] == 2:
            correct_normal += 1
        conf = r.get('confidence', 0)
        print(f"  {f}: {r['prediction_label']} ({conf:.0f}%)")

if total_normal > 0:
    print(f"Normal ECG Accuracy: {correct_normal}/{total_normal} = {correct_normal/total_normal*100:.1f}%")

print("\nTesting 30 MI ECGs...")
correct_mi = 0
total_mi = 0
for f in mi_files:
    img = MI_DIR / f
    r = predictor.predict_from_ecg_image(str(img))
    if r['success']:
        total_mi += 1
        if r['prediction_code'] == 1:
            correct_mi += 1
        conf = r.get('confidence', 0)
        print(f"  {f}: {r['prediction_label']} ({conf:.0f}%)")

if total_mi > 0:
    print(f"MI ECG Accuracy: {correct_mi}/{total_mi} = {correct_mi/total_mi*100:.1f}%")

total = total_normal + total_mi
correct = correct_normal + correct_mi
if total > 0:
    print(f"\n=== OVERALL ACCURACY: {correct}/{total} = {correct/total*100:.1f}% ===")
