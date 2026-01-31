"""
Improved Prediction Module for Real ML-based Yield Prediction
This module uses the trained Random Forest model instead of hardcoded values
"""

import joblib
import os
import numpy as np

class YieldPredictor:
    """
    Smart yield predictor that uses trained ML model when available,
    falls back to rule-based prediction otherwise
    """
    
    def __init__(self):
        self.model = None
        self.encoders = None
        self.feature_cols = None
        self.load_model()
    
    def load_model(self):
        """Load the trained model and encoders"""
        try:
            if os.path.exists('model.pkl'):
                self.model = joblib.load('model.pkl')
                self.encoders = joblib.load('encoders.pkl')
                self.feature_cols = joblib.load('feature_cols.pkl')
                print("✓ ML Model loaded successfully!")
                print(f"✓ Model type: {type(self.model).__name__}")
                print(f"✓ Features: {self.feature_cols}")
                return True
            else:
                print("⚠ No trained model found. Using fallback prediction.")
                return False
        except Exception as e:
            print(f"⚠ Error loading model: {e}")
            print("⚠ Using fallback prediction.")
            return False
    
    def predict_yield_ml(self, crop_name, area, soil_type, season, irrigation_type,
                        rainfall=750, temperature=27, humidity=70):
        """
        Predict yield using trained ML model
        
        Parameters:
        - crop_name: str (e.g., 'tomato', 'onion')
        - area: float (hectares)
        - soil_type: str ('loamy', 'clay', 'sandy', 'black')
        - season: str ('kharif', 'rabi', 'zaid')
        - irrigation_type: str ('drip', 'sprinkler', 'flood', 'rainfed')
        - rainfall: float (mm, default 750)
        - temperature: float (Celsius, default 27)
        - humidity: float (%, default 70)
        
        Returns:
        - predicted_yield: float (tons)
        """
        
        if not self.model:
            print("  Using fallback prediction (no ML model)")
            return self.predict_yield_fallback(crop_name, area, irrigation_type)
        
        try:
            # Encode categorical features
            crop_encoded = self.encoders['crop_name'].transform([crop_name.lower()])[0]
            soil_encoded = self.encoders['soil_type'].transform([soil_type.lower()])[0]
            season_encoded = self.encoders['season'].transform([season.lower()])[0]
            irrigation_encoded = self.encoders['irrigation_type'].transform([irrigation_type.lower()])[0]
            
            # Create feature array
            features = np.array([[
                crop_encoded,
                area,
                soil_encoded,
                season_encoded,
                irrigation_encoded,
                rainfall,
                temperature,
                humidity
            ]])
            
            # Predict
            prediction = self.model.predict(features)[0]
            
            print(f"  ML Prediction: {prediction:.2f} tons")
            print(f"  Input: {crop_name}, {area}ha, {soil_type}, {season}, {irrigation_type}")
            
            return round(prediction, 2)
            
        except Exception as e:
            print(f"  Error in ML prediction: {e}")
            print("  Falling back to rule-based prediction")
            return self.predict_yield_fallback(crop_name, area, irrigation_type)
    
    def predict_yield_fallback(self, crop_name, area, irrigation_type='drip'):
        """
        Fallback prediction using hardcoded averages
        (Used when ML model is not available)
        """
        # Average yields per hectare (tons)
        avg_yields = {
            'tomato': 5.5, 'onion': 4.5, 'potato': 6.5, 'wheat': 3.5, 'rice': 5.0,
            'cabbage': 4.0, 'cauliflower': 3.8, 'brinjal': 4.2, 'chili': 2.5
        }
        
        # Irrigation impact
        irrigation_multipliers = {
            'drip': 1.2, 'sprinkler': 1.1, 'flood': 1.0, 'rainfed': 0.85
        }
        
        base_yield = avg_yields.get(crop_name.lower(), 4.0)
        multiplier = irrigation_multipliers.get(irrigation_type.lower(), 1.0)
        
        prediction = area * base_yield * multiplier
        
        print(f"  Fallback Prediction: {prediction:.2f} tons")
        return round(prediction, 2)
    
    def get_prediction_confidence(self):
        """
        Return confidence level based on prediction method
        """
        if self.model:
            return {
                'level': 'HIGH',
                'method': 'Machine Learning (Random Forest)',
                'description': 'Based on trained model with weather and soil factors'
            }
        else:
            return {
                'level': 'MEDIUM',
                'method': 'Rule-based Estimation',
                'description': 'Based on historical average yields'
            }

# Global predictor instance
predictor = YieldPredictor()

def predict_yield(crop_name, area, soil_type='loamy', season='kharif', 
                 irrigation_type='drip', rainfall=750, temperature=27, humidity=70):
    """
    Main prediction function to be used in Flask app
    
    Usage:
        from prediction import predict_yield
        
        yield_tons = predict_yield(
            crop_name='tomato',
            area=2.5,
            soil_type='loamy',
            season='kharif',
            irrigation_type='drip'
        )
    """
    return predictor.predict_yield_ml(
        crop_name, area, soil_type, season, irrigation_type,
        rainfall, temperature, humidity
    )

def get_confidence():
    """
    Get prediction confidence information
    """
    return predictor.get_prediction_confidence()

# Example usage and testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print(" TESTING YIELD PREDICTION ")
    print("="*60)
    
    # Test cases
    test_cases = [
        {
            'crop_name': 'tomato',
            'area': 2.5,
            'soil_type': 'loamy',
            'season': 'kharif',
            'irrigation_type': 'drip',
            'rainfall': 800,
            'temperature': 28,
            'humidity': 65
        },
        {
            'crop_name': 'onion',
            'area': 5.0,
            'soil_type': 'black',
            'season': 'rabi',
            'irrigation_type': 'sprinkler',
            'rainfall': 600,
            'temperature': 25,
            'humidity': 60
        },
        {
            'crop_name': 'potato',
            'area': 3.0,
            'soil_type': 'sandy',
            'season': 'rabi',
            'irrigation_type': 'flood',
            'rainfall': 700,
            'temperature': 22,
            'humidity': 70
        }
    ]
    
    print("\nTesting predictions:")
    print("-" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        prediction = predict_yield(**test)
        print(f"Result: {prediction} tons\n")
    
    # Show confidence
    confidence = get_confidence()
    print("\n" + "="*60)
    print(f"Confidence Level: {confidence['level']}")
    print(f"Method: {confidence['method']}")
    print(f"Description: {confidence['description']}")
    print("="*60)