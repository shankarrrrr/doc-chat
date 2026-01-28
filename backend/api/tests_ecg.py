"""
Comprehensive tests for ECG Analysis functionality.
Tests the ECG service, API endpoint, and model predictions.
"""

import pytest
import os
import json
from pathlib import Path
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
import tempfile
import shutil


# ECG Dataset paths
ECG_DATASET_BASE = Path(r"C:\Users\Lenovo\Desktop\dyp\oop cp\Cardiovascular-Detection-using-ECG-images\ECG_IMAGES_DATASET")
NORMAL_ECG_DIR = ECG_DATASET_BASE / "Normal Person ECG Images (284x12=3408)"
MI_ECG_DIR = ECG_DATASET_BASE / "ECG Images of Myocardial Infarction Patients (240x12=2880)"
ABNORMAL_ECG_DIR = ECG_DATASET_BASE / "ECG Images of Patient that have abnormal heartbeat (233x12=2796)"
HISTORY_MI_DIR = ECG_DATASET_BASE / "ECG Images of Patient that have History of MI (172x12=2064)"


def get_test_image_path(category: str, index: int = 1) -> Path:
    """Get path to a test ECG image."""
    if category == "normal":
        return NORMAL_ECG_DIR / f"Normal({index}).jpg"
    elif category == "mi":
        return MI_ECG_DIR / f"MI({index}).jpg"
    elif category == "abnormal":
        return ABNORMAL_ECG_DIR / f"PMI({index}).jpg"
    elif category == "history_mi":
        return HISTORY_MI_DIR / f"HB({index}).jpg"
    return None


class TestECGServiceUnit(TestCase):
    """Unit tests for ECGPredictor service."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from api.ecg_service import ECGPredictor
        cls.predictor = ECGPredictor()
    
    def test_ecg_predictor_initialization(self):
        """Test ECGPredictor initializes correctly."""
        from api.ecg_service import ECGPredictor
        predictor = ECGPredictor()
        
        self.assertIsNotNone(predictor.models_dir)
        self.assertTrue(predictor.models_dir.exists())
    
    def test_models_exist(self):
        """Test that required ML models exist."""
        models_dir = self.predictor.models_dir
        
        pca_model = models_dir / "PCA_ECG (1).pkl"
        main_model = models_dir / "Heart_Disease_Prediction_using_ECG (4).pkl"
        scaler_model = models_dir / "scaler_ECG.pkl"
        
        self.assertTrue(pca_model.exists(), "PCA model not found")
        self.assertTrue(main_model.exists(), "Main prediction model not found")
        self.assertTrue(scaler_model.exists(), "Scaler model not found")
    
    def test_temp_workspace_creation(self):
        """Test temporary workspace creation and cleanup."""
        from api.ecg_service import ECGPredictor
        predictor = ECGPredictor()
        
        temp_dir = predictor.create_temp_workspace()
        self.assertTrue(os.path.exists(temp_dir))
        
        predictor.cleanup_temp_workspace()
        self.assertFalse(os.path.exists(temp_dir))
    
    def test_get_image_jpg(self):
        """Test loading a JPG ECG image."""
        test_image = get_test_image_path("normal", 1)
        if not test_image.exists():
            self.skipTest("Test image not found")
        
        image = self.predictor.get_image(str(test_image))
        
        self.assertIsNotNone(image)
        self.assertEqual(len(image.shape), 3)  # Should be RGB
        self.assertEqual(image.shape[2], 3)  # 3 channels
    
    def test_gray_image_conversion(self):
        """Test grayscale conversion and resizing."""
        test_image = get_test_image_path("normal", 1)
        if not test_image.exists():
            self.skipTest("Test image not found")
        
        image = self.predictor.get_image(str(test_image))
        gray = self.predictor.gray_image(image)
        
        self.assertEqual(len(gray.shape), 2)  # Grayscale is 2D
        self.assertEqual(gray.shape, (1572, 2213))  # Expected dimensions
    
    def test_divide_leads(self):
        """Test dividing ECG into 13 leads."""
        test_image = get_test_image_path("normal", 1)
        if not test_image.exists():
            self.skipTest("Test image not found")
        
        image = self.predictor.get_image(str(test_image))
        gray = self.predictor.gray_image(image)
        leads = self.predictor.divide_leads(gray)
        
        self.assertEqual(len(leads), 13)  # Should have 13 leads
        for i, lead in enumerate(leads):
            self.assertIsNotNone(lead, f"Lead {i+1} is None")


class TestECGPredictions(TestCase):
    """Integration tests for ECG predictions with real images."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from api.ecg_service import ECGPredictor
        cls.predictor = ECGPredictor()
    
    def test_predict_normal_ecg(self):
        """Test prediction on a normal ECG image."""
        test_image = get_test_image_path("normal", 1)
        if not test_image.exists():
            self.skipTest("Normal ECG test image not found")
        
        result = self.predictor.predict_from_ecg_image(str(test_image))
        
        self.assertTrue(result['success'], f"Prediction failed: {result.get('error')}")
        self.assertIn('prediction_code', result)
        self.assertIn('prediction_label', result)
        self.assertIn('prediction_message', result)
        self.assertIn(result['prediction_code'], [0, 1, 2, 3])
        print(f"Normal ECG prediction: {result['prediction_label']} (code: {result['prediction_code']})")
    
    def test_predict_mi_ecg(self):
        """Test prediction on MI ECG image."""
        test_image = get_test_image_path("mi", 1)
        if not test_image.exists():
            self.skipTest("MI ECG test image not found")
        
        result = self.predictor.predict_from_ecg_image(str(test_image))
        
        self.assertTrue(result['success'], f"Prediction failed: {result.get('error')}")
        self.assertIn('prediction_code', result)
        print(f"MI ECG prediction: {result['prediction_label']} (code: {result['prediction_code']})")
    
    def test_predict_multiple_normal_images(self):
        """Test predictions on multiple normal ECG images."""
        predictions = []
        for i in [1, 5, 10, 20, 50]:
            test_image = get_test_image_path("normal", i)
            if test_image.exists():
                result = self.predictor.predict_from_ecg_image(str(test_image))
                if result['success']:
                    predictions.append(result['prediction_code'])
        
        if not predictions:
            self.skipTest("No normal ECG images found")
        
        print(f"Normal ECG predictions: {predictions}")
        # Check that we got valid predictions
        for pred in predictions:
            self.assertIn(pred, [0, 1, 2, 3])
    
    def test_predict_multiple_mi_images(self):
        """Test predictions on multiple MI ECG images."""
        predictions = []
        for i in [1, 5, 10, 20, 50]:
            test_image = get_test_image_path("mi", i)
            if test_image.exists():
                result = self.predictor.predict_from_ecg_image(str(test_image))
                if result['success']:
                    predictions.append(result['prediction_code'])
        
        if not predictions:
            self.skipTest("No MI ECG images found")
        
        print(f"MI ECG predictions: {predictions}")
        for pred in predictions:
            self.assertIn(pred, [0, 1, 2, 3])
    
    def test_prediction_includes_confidence(self):
        """Test that predictions include confidence score when available."""
        test_image = get_test_image_path("normal", 1)
        if not test_image.exists():
            self.skipTest("Test image not found")
        
        result = self.predictor.predict_from_ecg_image(str(test_image))
        
        self.assertTrue(result['success'])
        # Confidence may or may not be available depending on model
        if result.get('confidence'):
            self.assertGreaterEqual(result['confidence'], 0)
            self.assertLessEqual(result['confidence'], 100)
    
    def test_prediction_includes_status(self):
        """Test that predictions include status field."""
        test_image = get_test_image_path("normal", 1)
        if not test_image.exists():
            self.skipTest("Test image not found")
        
        result = self.predictor.predict_from_ecg_image(str(test_image))
        
        self.assertTrue(result['success'])
        self.assertIn('status', result)
        self.assertIn(result['status'], ['normal', 'attention', 'critical'])


class TestECGAPIEndpoint(TestCase):
    """Integration tests for the ECG API endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    def _create_mock_auth(self):
        """Create mock authentication for tests."""
        from api.models import Profile
        import uuid
        
        # Create a test profile
        test_uid = uuid.uuid4()
        profile = Profile.objects.create(
            supabase_uid=test_uid,
            email="test@example.com",
            full_name="Test User",
            onboarding_completed=True
        )
        return profile, str(test_uid)
    
    @patch('api.decorators.verify_supabase_token')
    def test_ecg_endpoint_no_file(self, mock_verify):
        """Test ECG endpoint returns error when no file provided."""
        from api.supabase_auth import SupabaseUser
        
        profile, uid = self._create_mock_auth()
        mock_verify.return_value = SupabaseUser(
            id=uid,
            email="test@example.com",
            user_metadata={}
        )
        
        response = self.client.post(
            '/api/ecg/analyze/',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('detail', data)
    
    @patch('api.decorators.verify_supabase_token')
    def test_ecg_endpoint_invalid_file_type(self, mock_verify):
        """Test ECG endpoint rejects non-image files."""
        from api.supabase_auth import SupabaseUser
        
        profile, uid = self._create_mock_auth()
        mock_verify.return_value = SupabaseUser(
            id=uid,
            email="test@example.com",
            user_metadata={}
        )
        
        fake_file = SimpleUploadedFile(
            "test.txt",
            b"not an image",
            content_type="text/plain"
        )
        
        response = self.client.post(
            '/api/ecg/analyze/',
            {'ecg_image': fake_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 400)
    
    @patch('api.decorators.verify_supabase_token')
    def test_ecg_endpoint_with_real_image(self, mock_verify):
        """Test ECG endpoint with a real ECG image."""
        from api.supabase_auth import SupabaseUser
        
        test_image_path = get_test_image_path("normal", 1)
        if not test_image_path.exists():
            self.skipTest("Test image not found")
        
        profile, uid = self._create_mock_auth()
        mock_verify.return_value = SupabaseUser(
            id=uid,
            email="test@example.com",
            user_metadata={}
        )
        
        with open(test_image_path, 'rb') as img_file:
            image_content = img_file.read()
        
        uploaded_file = SimpleUploadedFile(
            "test_ecg.jpg",
            image_content,
            content_type="image/jpeg"
        )
        
        response = self.client.post(
            '/api/ecg/analyze/',
            {'ecg_image': uploaded_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data.get('success'), f"Response: {data}")
        self.assertIn('prediction', data)
        self.assertIn('label', data['prediction'])
        self.assertIn('message', data['prediction'])
        self.assertIn('record', data)
        
        print(f"API Response - Prediction: {data['prediction']['label']}")
    
    @patch('api.decorators.verify_supabase_token')
    def test_ecg_creates_medical_record(self, mock_verify):
        """Test that ECG analysis creates a medical record."""
        from api.supabase_auth import SupabaseUser
        from api.models import MedicalRecord
        
        test_image_path = get_test_image_path("normal", 1)
        if not test_image_path.exists():
            self.skipTest("Test image not found")
        
        profile, uid = self._create_mock_auth()
        mock_verify.return_value = SupabaseUser(
            id=uid,
            email="test@example.com",
            user_metadata={}
        )
        
        initial_count = MedicalRecord.objects.filter(profile=profile).count()
        
        with open(test_image_path, 'rb') as img_file:
            image_content = img_file.read()
        
        uploaded_file = SimpleUploadedFile(
            "test_ecg.jpg",
            image_content,
            content_type="image/jpeg"
        )
        
        response = self.client.post(
            '/api/ecg/analyze/',
            {'ecg_image': uploaded_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        
        final_count = MedicalRecord.objects.filter(profile=profile).count()
        self.assertEqual(final_count, initial_count + 1)
        
        # Check record details
        record = MedicalRecord.objects.filter(profile=profile).last()
        self.assertEqual(record.category, 'imaging')
        self.assertIn('ECG Analysis', record.title)
        self.assertEqual(record.doctor, 'AI Analysis')


class TestECGModelAccuracy(TestCase):
    """Tests to evaluate model prediction accuracy on known samples."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from api.ecg_service import ECGPredictor
        cls.predictor = ECGPredictor()
    
    def test_batch_normal_predictions(self):
        """Test batch predictions on normal ECG images and report accuracy."""
        correct = 0
        total = 0
        results = []
        
        for i in range(1, 21):  # Test first 20 images
            test_image = NORMAL_ECG_DIR / f"Normal({i}).jpg"
            if test_image.exists():
                result = self.predictor.predict_from_ecg_image(str(test_image))
                if result['success']:
                    total += 1
                    # Code 2 = Normal
                    if result['prediction_code'] == 2:
                        correct += 1
                    results.append({
                        'image': f"Normal({i}).jpg",
                        'predicted': result['prediction_label'],
                        'code': result['prediction_code']
                    })
        
        if total > 0:
            accuracy = (correct / total) * 100
            print(f"\n=== Normal ECG Batch Test ===")
            print(f"Total tested: {total}")
            print(f"Correctly identified as Normal: {correct}")
            print(f"Accuracy: {accuracy:.1f}%")
            print(f"Results: {results}")
    
    def test_batch_mi_predictions(self):
        """Test batch predictions on MI ECG images and report accuracy."""
        correct = 0
        total = 0
        results = []
        
        for i in range(1, 21):  # Test first 20 images
            test_image = MI_ECG_DIR / f"MI({i}).jpg"
            if test_image.exists():
                result = self.predictor.predict_from_ecg_image(str(test_image))
                if result['success']:
                    total += 1
                    # Code 1 = MI
                    if result['prediction_code'] == 1:
                        correct += 1
                    results.append({
                        'image': f"MI({i}).jpg",
                        'predicted': result['prediction_label'],
                        'code': result['prediction_code']
                    })
        
        if total > 0:
            accuracy = (correct / total) * 100
            print(f"\n=== MI ECG Batch Test ===")
            print(f"Total tested: {total}")
            print(f"Correctly identified as MI: {correct}")
            print(f"Accuracy: {accuracy:.1f}%")
            print(f"Results: {results}")
    
    def test_prediction_distribution(self):
        """Test overall prediction distribution across all categories."""
        categories = {
            'normal': (NORMAL_ECG_DIR, 'Normal', 5),
            'mi': (MI_ECG_DIR, 'MI', 5),
        }
        
        all_results = []
        prediction_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        
        for cat_name, (dir_path, prefix, count) in categories.items():
            for i in range(1, count + 1):
                test_image = dir_path / f"{prefix}({i}).jpg"
                if test_image.exists():
                    result = self.predictor.predict_from_ecg_image(str(test_image))
                    if result['success']:
                        prediction_counts[result['prediction_code']] += 1
                        all_results.append({
                            'category': cat_name,
                            'predicted': result['prediction_label']
                        })
        
        print(f"\n=== Prediction Distribution ===")
        print(f"Abnormal Heartbeat (0): {prediction_counts[0]}")
        print(f"Myocardial Infarction (1): {prediction_counts[1]}")
        print(f"Normal (2): {prediction_counts[2]}")
        print(f"History of MI (3): {prediction_counts[3]}")


class TestECGErrorHandling(TestCase):
    """Tests for error handling in ECG service."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from api.ecg_service import ECGPredictor
        cls.predictor = ECGPredictor()
    
    def test_invalid_image_path(self):
        """Test handling of invalid image path."""
        result = self.predictor.predict_from_ecg_image("/nonexistent/path/image.jpg")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_corrupted_image_handling(self):
        """Test handling of corrupted/invalid image data."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b"not a valid image")
            temp_path = f.name
        
        try:
            result = self.predictor.predict_from_ecg_image(temp_path)
            # Should either fail gracefully or handle the error
            if not result['success']:
                self.assertIn('error', result)
        finally:
            os.unlink(temp_path)
    
    def test_empty_file_handling(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
        
        try:
            result = self.predictor.predict_from_ecg_image(temp_path)
            self.assertFalse(result['success'])
        finally:
            os.unlink(temp_path)


# Run a quick validation test
def run_quick_validation():
    """Run a quick validation to ensure ECG analysis is working."""
    from api.ecg_service import ECGPredictor
    
    print("=" * 60)
    print("ECG Analysis Quick Validation")
    print("=" * 60)
    
    predictor = ECGPredictor()
    
    # Test with one image from each category
    test_cases = [
        ("Normal", NORMAL_ECG_DIR / "Normal(1).jpg", 2),
        ("MI", MI_ECG_DIR / "MI(1).jpg", 1),
    ]
    
    for name, path, expected_code in test_cases:
        if path.exists():
            print(f"\nTesting {name} ECG...")
            result = predictor.predict_from_ecg_image(str(path))
            
            if result['success']:
                print(f"  Prediction: {result['prediction_label']}")
                print(f"  Code: {result['prediction_code']} (expected: {expected_code})")
                print(f"  Message: {result['prediction_message'][:50]}...")
                if result.get('confidence'):
                    print(f"  Confidence: {result['confidence']:.1f}%")
                print(f"  Status: {result['status']}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"\nSkipping {name} - image not found")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    run_quick_validation()
