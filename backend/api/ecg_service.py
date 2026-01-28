"""
ECG-based Heart Disease Prediction Service
Adapted from: Cardiovascular-Detection-using-ECG-images
"""

from skimage.io import imread
from skimage import color
import matplotlib
matplotlib.use('Agg')
from skimage.filters import threshold_otsu, gaussian
from skimage.transform import resize
from skimage import measure
import joblib
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
import os
from pathlib import Path
import tempfile
import shutil


class ECGPredictor:
    """
    ECG Image Analysis and Heart Disease Prediction
    
    Processes 12-lead ECG images to detect:
    - Normal heart
    - Myocardial Infarction (Heart Attack)
    - Abnormal Heartbeat (Arrhythmia)
    - History of Myocardial Infarction
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.models_dir = self.base_dir / 'ecg_models'
        self.temp_dir = None
        
    def create_temp_workspace(self):
        self.temp_dir = tempfile.mkdtemp()
        return self.temp_dir
    
    def cleanup_temp_workspace(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    def get_image(self, image_path):
        image = imread(image_path)
        
        if len(image.shape) == 2:
            image = np.stack([image, image, image], axis=-1)
        elif len(image.shape) == 3:
            if image.shape[2] == 4:
                image = image[:, :, :3]
            elif image.shape[2] == 2:
                image = np.stack([image[:, :, 0], image[:, :, 0], image[:, :, 0]], axis=-1)
            elif image.shape[2] == 1:
                image = np.concatenate([image, image, image], axis=-1)
        
        return image
    
    def gray_image(self, image):
        if len(image.shape) == 2:
            image_gray = image
        else:
            if image.shape[2] == 4:
                image = image[:, :, :3]
            elif image.shape[2] == 2:
                image = np.stack([image[:, :, 0], image[:, :, 0], image[:, :, 0]], axis=-1)
            elif image.shape[2] == 1:
                image = np.concatenate([image, image, image], axis=-1)
            image_gray = color.rgb2gray(image)
        
        image_gray = resize(image_gray, (1572, 2213))
        return image_gray
    
    def divide_leads(self, image):
        Lead_1 = image[300:600, 150:643]
        Lead_2 = image[300:600, 646:1135]
        Lead_3 = image[300:600, 1140:1625]
        Lead_4 = image[300:600, 1630:2125]
        Lead_5 = image[600:900, 150:643]
        Lead_6 = image[600:900, 646:1135]
        Lead_7 = image[600:900, 1140:1625]
        Lead_8 = image[600:900, 1630:2125]
        Lead_9 = image[900:1200, 150:643]
        Lead_10 = image[900:1200, 646:1135]
        Lead_11 = image[900:1200, 1140:1625]
        Lead_12 = image[900:1200, 1630:2125]
        Lead_13 = image[1250:1480, 150:2125]
        
        return [Lead_1, Lead_2, Lead_3, Lead_4, Lead_5, Lead_6, 
                Lead_7, Lead_8, Lead_9, Lead_10, Lead_11, Lead_12, Lead_13]
    
    def signal_extraction_scaling(self, Leads):
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)
        
        try:
            for x, y in enumerate(Leads[:len(Leads)-1]):
                if len(y.shape) == 2:
                    grayscale = y
                else:
                    if y.shape[2] == 4:
                        y = y[:, :, :3]
                    elif y.shape[2] == 2:
                        y = np.stack([y[:, :, 0], y[:, :, 0], y[:, :, 0]], axis=-1)
                    elif y.shape[2] == 1:
                        y = np.concatenate([y, y, y], axis=-1)
                    grayscale = color.rgb2gray(y)
                
                blurred_image = gaussian(grayscale, sigma=0.7)
                global_thresh = threshold_otsu(blurred_image)
                binary_global = blurred_image < global_thresh
                binary_global = resize(binary_global, (300, 450))
                
                contours = measure.find_contours(binary_global, 0.8)
                contours_shape = sorted([c.shape for c in contours])[::-1][0:1]
                
                test = None
                for contour in contours:
                    if contour.shape in contours_shape:
                        test = resize(contour, (255, 2))
                
                if test is None:
                    test = np.zeros((255, 2))
                
                lead_no = x
                scaler = MinMaxScaler()
                fit_transform_data = scaler.fit_transform(test)
                Normalized_Scaled = pd.DataFrame(fit_transform_data[:, 0], columns=['X'])
                Normalized_Scaled = Normalized_Scaled.T
                
                csv_filename = f'Scaled_1DLead_{lead_no+1}.csv'
                Normalized_Scaled.to_csv(csv_filename, index=False)
        
        finally:
            os.chdir(original_dir)
    
    def combine_convert_1d_signal(self):
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)
        
        try:
            test_final = pd.read_csv('Scaled_1DLead_1.csv')
            
            from natsort import natsorted
            for files in natsorted(os.listdir('.')):
                if files.endswith(".csv") and files != 'Scaled_1DLead_1.csv':
                    df = pd.read_csv(files)
                    test_final = pd.concat([test_final, df], axis=1, ignore_index=True)
            
            return test_final
        
        finally:
            os.chdir(original_dir)
    
    def dimensional_reduction(self, test_final):
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
        
        scaler_path = self.models_dir / 'scaler_ECG.pkl'
        if scaler_path.exists():
            scaler = joblib.load(scaler_path)
            test_scaled = scaler.transform(test_final)
        else:
            test_scaled = test_final
        
        pca_model_path = self.models_dir / 'PCA_ECG (1).pkl'
        pca_loaded_model = joblib.load(pca_model_path)
        result = pca_loaded_model.transform(test_scaled)
        final_df = pd.DataFrame(result)
        return final_df
    
    def model_load_predict(self, final_df):
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
        
        try:
            model_path = self.models_dir / 'Heart_Disease_Prediction_using_ECG (4).pkl'
            loaded_model = joblib.load(model_path)
            result = loaded_model.predict(final_df)
            
            try:
                proba = loaded_model.predict_proba(final_df)
                confidence = float(np.max(proba) * 100)
            except:
                confidence = None
            
            prediction_map = {
                0: ("Abnormal Heartbeat", "Your ECG shows signs of abnormal heartbeat (arrhythmia). Please consult a cardiologist.", "attention"),
                1: ("Myocardial Infarction", "Your ECG indicates Myocardial Infarction (heart attack). Seek immediate medical attention!", "critical"),
                2: ("Normal", "Your ECG appears normal. Your heart rhythm is healthy.", "normal"),
                3: ("History of MI", "Your ECG shows signs of previous Myocardial Infarction. Follow up with your cardiologist.", "attention")
            }
            
            pred_code = int(result[0])
            pred_label, pred_message, status = prediction_map.get(pred_code, ("Unknown", "Unable to classify ECG", "attention"))
            
            return pred_code, pred_label, pred_message, confidence, status
            
        except Exception as e:
            error_msg = str(e)
            if 'dtype' in error_msg or 'incompatible' in error_msg.lower():
                raise Exception(
                    "ECG model incompatibility detected. Please retrain the models or use compatible versions."
                )
            else:
                raise
    
    def predict_from_ecg_image(self, image_path):
        try:
            self.create_temp_workspace()
            
            ecg_image = self.get_image(image_path)
            gray_image = self.gray_image(ecg_image)
            leads = self.divide_leads(gray_image)
            self.signal_extraction_scaling(leads)
            combined_signal = self.combine_convert_1d_signal()
            reduced_features = self.dimensional_reduction(combined_signal)
            pred_code, pred_label, pred_message, confidence, status = self.model_load_predict(reduced_features)
            
            result = {
                'success': True,
                'prediction_code': pred_code,
                'prediction_label': pred_label,
                'prediction_message': pred_message,
                'confidence': confidence,
                'status': status,
                'num_features': combined_signal.shape[1],
                'reduced_features': reduced_features.shape[1]
            }
            
            return result
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'prediction_label': 'Error',
                'prediction_message': f'Failed to process ECG image: {str(e)}',
                'status': 'attention'
            }
        
        finally:
            self.cleanup_temp_workspace()
