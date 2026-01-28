"""
Standalone ECG test runner - tests ECG functionality without Django DB
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from api.ecg_service import ECGPredictor

# ECG Dataset paths
ECG_DATASET_BASE = Path(r"C:\Users\Lenovo\Desktop\dyp\oop cp\Cardiovascular-Detection-using-ECG-images\ECG_IMAGES_DATASET")
NORMAL_ECG_DIR = ECG_DATASET_BASE / "Normal Person ECG Images (284x12=3408)"
MI_ECG_DIR = ECG_DATASET_BASE / "ECG Images of Myocardial Infarction Patients (240x12=2880)"
ABNORMAL_ECG_DIR = ECG_DATASET_BASE / "ECG Images of Patient that have abnormal heartbeat (233x12=2796)"
HISTORY_MI_DIR = ECG_DATASET_BASE / "ECG Images of Patient that have History of MI (172x12=2064)"


def test_ecg_service_initialization():
    """Test ECGPredictor initializes correctly."""
    print("\n[TEST] ECG Service Initialization")
    predictor = ECGPredictor()
    
    assert predictor.models_dir.exists(), "Models directory not found"
    print("  [OK] Models directory exists")
    
    pca_model = predictor.models_dir / "PCA_ECG (1).pkl"
    main_model = predictor.models_dir / "Heart_Disease_Prediction_using_ECG (4).pkl"
    scaler_model = predictor.models_dir / "scaler_ECG.pkl"
    
    assert pca_model.exists(), "PCA model not found"
    print("  [OK] PCA model exists")
    
    assert main_model.exists(), "Main model not found"
    print("  [OK] Main prediction model exists")
    
    assert scaler_model.exists(), "Scaler model not found"
    print("  [OK] Scaler model exists")
    
    return True


def test_temp_workspace():
    """Test temporary workspace creation and cleanup."""
    print("\n[TEST] Temporary Workspace")
    predictor = ECGPredictor()
    
    temp_dir = predictor.create_temp_workspace()
    assert os.path.exists(temp_dir), "Temp directory not created"
    print(f"  [OK] Created temp workspace: {temp_dir}")
    
    predictor.cleanup_temp_workspace()
    assert not os.path.exists(temp_dir), "Temp directory not cleaned up"
    print("  [OK] Cleaned up temp workspace")
    
    return True


def test_image_loading():
    """Test loading ECG images."""
    print("\n[TEST] Image Loading")
    predictor = ECGPredictor()
    
    test_image = NORMAL_ECG_DIR / "Normal(1).jpg"
    if not test_image.exists():
        print("  [SKIP] Test image not found")
        return True
    
    image = predictor.get_image(str(test_image))
    assert image is not None, "Image is None"
    assert len(image.shape) == 3, "Image should be 3D (RGB)"
    assert image.shape[2] == 3, "Image should have 3 channels"
    print(f"  [OK] Loaded image with shape: {image.shape}")
    
    return True


def test_grayscale_conversion():
    """Test grayscale conversion."""
    print("\n[TEST] Grayscale Conversion")
    predictor = ECGPredictor()
    
    test_image = NORMAL_ECG_DIR / "Normal(1).jpg"
    if not test_image.exists():
        print("  [SKIP] Test image not found")
        return True
    
    image = predictor.get_image(str(test_image))
    gray = predictor.gray_image(image)
    
    assert len(gray.shape) == 2, "Grayscale should be 2D"
    assert gray.shape == (1572, 2213), f"Unexpected shape: {gray.shape}"
    print(f"  [OK] Converted to grayscale with shape: {gray.shape}")
    
    return True


def test_lead_division():
    """Test dividing ECG into leads."""
    print("\n[TEST] Lead Division")
    predictor = ECGPredictor()
    
    test_image = NORMAL_ECG_DIR / "Normal(1).jpg"
    if not test_image.exists():
        print("  [SKIP] Test image not found")
        return True
    
    image = predictor.get_image(str(test_image))
    gray = predictor.gray_image(image)
    leads = predictor.divide_leads(gray)
    
    assert len(leads) == 13, f"Expected 13 leads, got {len(leads)}"
    print(f"  [OK] Divided into {len(leads)} leads")
    
    for i, lead in enumerate(leads):
        assert lead is not None, f"Lead {i+1} is None"
    print("  [OK] All leads are valid")
    
    return True


def test_normal_ecg_prediction():
    """Test prediction on normal ECG."""
    print("\n[TEST] Normal ECG Prediction")
    predictor = ECGPredictor()
    
    test_image = NORMAL_ECG_DIR / "Normal(1).jpg"
    if not test_image.exists():
        print("  [SKIP] Test image not found")
        return True
    
    result = predictor.predict_from_ecg_image(str(test_image))
    
    assert result['success'], f"Prediction failed: {result.get('error')}"
    assert 'prediction_code' in result
    assert 'prediction_label' in result
    assert 'prediction_message' in result
    assert result['prediction_code'] in [0, 1, 2, 3]
    
    print(f"  [OK] Prediction: {result['prediction_label']}")
    print(f"  [OK] Code: {result['prediction_code']}")
    if result.get('confidence'):
        print(f"  [OK] Confidence: {result['confidence']:.1f}%")
    print(f"  [OK] Status: {result['status']}")
    
    return True


def test_mi_ecg_prediction():
    """Test prediction on MI ECG."""
    print("\n[TEST] MI ECG Prediction")
    predictor = ECGPredictor()
    
    test_image = MI_ECG_DIR / "MI(1).jpg"
    if not test_image.exists():
        print("  [SKIP] Test image not found")
        return True
    
    result = predictor.predict_from_ecg_image(str(test_image))
    
    assert result['success'], f"Prediction failed: {result.get('error')}"
    
    print(f"  [OK] Prediction: {result['prediction_label']}")
    print(f"  [OK] Code: {result['prediction_code']}")
    if result.get('confidence'):
        print(f"  [OK] Confidence: {result['confidence']:.1f}%")
    print(f"  [OK] Status: {result['status']}")
    
    return True


def test_batch_normal_predictions():
    """Test batch predictions on normal ECGs."""
    print("\n[TEST] Batch Normal ECG Predictions (20 images)")
    predictor = ECGPredictor()
    
    correct = 0
    total = 0
    
    for i in range(1, 21):
        test_image = NORMAL_ECG_DIR / f"Normal({i}).jpg"
        if test_image.exists():
            result = predictor.predict_from_ecg_image(str(test_image))
            if result['success']:
                total += 1
                if result['prediction_code'] == 2:  # Normal
                    correct += 1
    
    if total > 0:
        accuracy = (correct / total) * 100
        print(f"  Total tested: {total}")
        print(f"  Correctly identified as Normal: {correct}")
        print(f"  [OK] Accuracy: {accuracy:.1f}%")
    else:
        print("  [SKIP] No images found")
    
    return True


def test_batch_mi_predictions():
    """Test batch predictions on MI ECGs."""
    print("\n[TEST] Batch MI ECG Predictions (20 images)")
    predictor = ECGPredictor()
    
    correct = 0
    total = 0
    
    for i in range(1, 21):
        test_image = MI_ECG_DIR / f"MI({i}).jpg"
        if test_image.exists():
            result = predictor.predict_from_ecg_image(str(test_image))
            if result['success']:
                total += 1
                if result['prediction_code'] == 1:  # MI
                    correct += 1
    
    if total > 0:
        accuracy = (correct / total) * 100
        print(f"  Total tested: {total}")
        print(f"  Correctly identified as MI: {correct}")
        print(f"  [OK] Accuracy: {accuracy:.1f}%")
    else:
        print("  [SKIP] No images found")
    
    return True


def test_error_handling():
    """Test error handling."""
    print("\n[TEST] Error Handling")
    predictor = ECGPredictor()
    
    # Test invalid path
    result = predictor.predict_from_ecg_image("/nonexistent/path.jpg")
    assert not result['success'], "Should fail for invalid path"
    assert 'error' in result
    print("  [OK] Handles invalid path correctly")
    
    return True


def test_prediction_distribution():
    """Test prediction distribution across categories."""
    print("\n[TEST] Prediction Distribution (5 images per category)")
    predictor = ECGPredictor()
    
    categories = {
        'Normal': (NORMAL_ECG_DIR, 'Normal'),
        'MI': (MI_ECG_DIR, 'MI'),
    }
    
    prediction_map = {0: 'Abnormal', 1: 'MI', 2: 'Normal', 3: 'History MI'}
    
    for cat_name, (dir_path, prefix) in categories.items():
        print(f"\n  {cat_name} ECGs:")
        for i in range(1, 6):
            test_image = dir_path / f"{prefix}({i}).jpg"
            if test_image.exists():
                result = predictor.predict_from_ecg_image(str(test_image))
                if result['success']:
                    conf = f" ({result['confidence']:.0f}%)" if result.get('confidence') else ""
                    print(f"    {prefix}({i}): {result['prediction_label']}{conf}")
    
    return True


def run_all_tests():
    """Run all ECG tests."""
    print("=" * 70)
    print("ECG ANALYSIS - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Service Initialization", test_ecg_service_initialization),
        ("Temp Workspace", test_temp_workspace),
        ("Image Loading", test_image_loading),
        ("Grayscale Conversion", test_grayscale_conversion),
        ("Lead Division", test_lead_division),
        ("Normal ECG Prediction", test_normal_ecg_prediction),
        ("MI ECG Prediction", test_mi_ecg_prediction),
        ("Error Handling", test_error_handling),
        ("Batch Normal Predictions", test_batch_normal_predictions),
        ("Batch MI Predictions", test_batch_mi_predictions),
        ("Prediction Distribution", test_prediction_distribution),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n  [FAILED]: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
