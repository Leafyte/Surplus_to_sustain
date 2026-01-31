"""
Machine Learning Model Training for Crop Yield Prediction
This script generates synthetic training data and trains a Random Forest model
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

# Set random seed for reproducibility
np.random.seed(42)

def generate_synthetic_crop_data(n_samples=2000):
    """
    Generate synthetic crop yield data based on realistic agricultural patterns
    """
    print(f"Generating {n_samples} synthetic crop records...")
    
    crops = ['tomato', 'onion', 'potato', 'wheat', 'rice', 'cabbage', 'cauliflower', 'brinjal', 'chili']
    soil_types = ['loamy', 'clay', 'sandy', 'black']
    seasons = ['kharif', 'rabi', 'zaid']
    irrigation_types = ['drip', 'sprinkler', 'flood', 'rainfed']
    
    # Base yields (tons per hectare) - realistic averages
    base_yields = {
        'tomato': 5.5, 'onion': 4.5, 'potato': 6.5, 'wheat': 3.5, 'rice': 5.0,
        'cabbage': 4.0, 'cauliflower': 3.8, 'brinjal': 4.2, 'chili': 2.5
    }
    
    # Impact factors
    soil_multipliers = {'loamy': 1.1, 'clay': 0.95, 'sandy': 0.85, 'black': 1.05}
    irrigation_multipliers = {'drip': 1.2, 'sprinkler': 1.1, 'flood': 1.0, 'rainfed': 0.85}
    season_multipliers = {'kharif': 1.0, 'rabi': 1.05, 'zaid': 0.95}
    
    data = []
    
    for _ in range(n_samples):
        crop = np.random.choice(crops)
        soil = np.random.choice(soil_types)
        season = np.random.choice(seasons)
        irrigation = np.random.choice(irrigation_types)
        
        # Random area between 0.5 and 10 hectares
        area = np.random.uniform(0.5, 10)
        
        # Random weather factors
        rainfall = np.random.uniform(300, 1200)  # mm
        temperature = np.random.uniform(20, 35)  # Celsius
        humidity = np.random.uniform(50, 90)  # percentage
        
        # Calculate base yield
        base_yield = base_yields[crop]
        
        # Apply multipliers
        yield_per_hectare = (base_yield * 
                            soil_multipliers[soil] * 
                            irrigation_multipliers[irrigation] * 
                            season_multipliers[season])
        
        # Add weather impact
        rainfall_factor = 1 + (rainfall - 750) / 5000  # Optimal around 750mm
        temp_factor = 1 - abs(temperature - 27) / 100  # Optimal around 27°C
        humidity_factor = 1 - abs(humidity - 70) / 200  # Optimal around 70%
        
        yield_per_hectare *= (rainfall_factor * temp_factor * humidity_factor)
        
        # Add random variation (+/- 20%)
        yield_per_hectare *= np.random.uniform(0.8, 1.2)
        
        # Total yield
        total_yield = area * yield_per_hectare
        
        data.append({
            'crop_name': crop,
            'area': round(area, 2),
            'soil_type': soil,
            'season': season,
            'irrigation_type': irrigation,
            'rainfall': round(rainfall, 1),
            'temperature': round(temperature, 1),
            'humidity': round(humidity, 1),
            'yield_tons': round(total_yield, 2)
        })
    
    df = pd.DataFrame(data)
    print(f"✓ Generated {len(df)} records")
    print(f"\nDataset shape: {df.shape}")
    print(f"\nSample data:")
    print(df.head())
    
    return df

def encode_features(df):
    """
    Encode categorical features
    """
    print("\nEncoding categorical features...")
    
    df_encoded = df.copy()
    
    # Create label encoders
    encoders = {}
    categorical_cols = ['crop_name', 'soil_type', 'season', 'irrigation_type']
    
    for col in categorical_cols:
        encoder = LabelEncoder()
        df_encoded[f'{col}_encoded'] = encoder.fit_transform(df[col])
        encoders[col] = encoder
        print(f"  {col}: {len(encoder.classes_)} classes")
    
    return df_encoded, encoders

def train_model(df):
    """
    Train Random Forest model
    """
    print("\n" + "="*50)
    print("TRAINING MACHINE LEARNING MODEL")
    print("="*50)
    
    # Encode features
    df_encoded, encoders = encode_features(df)
    
    # Select features
    feature_cols = [
        'crop_name_encoded', 'area', 'soil_type_encoded', 
        'season_encoded', 'irrigation_type_encoded',
        'rainfall', 'temperature', 'humidity'
    ]
    
    X = df_encoded[feature_cols]
    y = df_encoded['yield_tons']
    
    print(f"\nFeatures: {feature_cols}")
    print(f"Target: yield_tons")
    print(f"Total samples: {len(X)}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")
    
    # Train Random Forest
    print("\nTraining Random Forest Regressor...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    print("✓ Model trained successfully!")
    
    # Evaluate
    print("\n" + "="*50)
    print("MODEL EVALUATION")
    print("="*50)
    
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Training metrics
    train_mae = mean_absolute_error(y_train, y_pred_train)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    train_r2 = r2_score(y_train, y_pred_train)
    
    # Testing metrics
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_r2 = r2_score(y_test, y_pred_test)
    
    print("\nTraining Set:")
    print(f"  MAE:  {train_mae:.2f} tons")
    print(f"  RMSE: {train_rmse:.2f} tons")
    print(f"  R² Score: {train_r2:.4f}")
    
    print("\nTesting Set:")
    print(f"  MAE:  {test_mae:.2f} tons")
    print(f"  RMSE: {test_rmse:.2f} tons")
    print(f"  R² Score: {test_r2:.4f}")
    
    # Feature importance
    print("\nFeature Importance:")
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    # Example predictions
    print("\n" + "="*50)
    print("EXAMPLE PREDICTIONS")
    print("="*50)
    
    sample_indices = np.random.choice(len(X_test), 5, replace=False)
    
    for idx in sample_indices:
        actual = y_test.iloc[idx]
        predicted = y_pred_test[idx]
        original_idx = y_test.index[idx]
        
        crop = df.loc[original_idx, 'crop_name']
        area = df.loc[original_idx, 'area']
        soil = df.loc[original_idx, 'soil_type']
        irrigation = df.loc[original_idx, 'irrigation_type']
        
        print(f"\n{crop.title()} ({area} hectares, {soil} soil, {irrigation} irrigation)")
        print(f"  Actual:    {actual:.2f} tons")
        print(f"  Predicted: {predicted:.2f} tons")
        print(f"  Error:     {abs(actual - predicted):.2f} tons ({abs(actual - predicted)/actual*100:.1f}%)")
    
    return model, encoders, feature_cols, X_test, y_test, y_pred_test

def save_model(model, encoders, feature_cols):
    """
    Save the trained model and encoders
    """
    print("\n" + "="*50)
    print("SAVING MODEL")
    print("="*50)
    
    # Save model
    joblib.dump(model, 'model.pkl')
    print("✓ Model saved as 'model.pkl'")
    
    # Save encoders
    joblib.dump(encoders, 'encoders.pkl')
    print("✓ Encoders saved as 'encoders.pkl'")
    
    # Save feature columns
    joblib.dump(feature_cols, 'feature_cols.pkl')
    print("✓ Feature columns saved as 'feature_cols.pkl'")
    
    print("\nModel files ready to use in Flask app!")

def create_visualizations(df, X_test, y_test, y_pred_test):
    """
    Create visualization plots
    """
    print("\nCreating visualizations...")
    
    # Set style
    sns.set_style("whitegrid")
    
    # 1. Actual vs Predicted
    plt.figure(figsize=(10, 6))
    plt.scatter(y_test, y_pred_test, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
    plt.xlabel('Actual Yield (tons)')
    plt.ylabel('Predicted Yield (tons)')
    plt.title('Actual vs Predicted Crop Yield')
    plt.tight_layout()
    plt.savefig('prediction_accuracy.png', dpi=150)
    print("✓ Saved 'prediction_accuracy.png'")
    plt.close()
    
    # 2. Yield distribution by crop
    plt.figure(figsize=(12, 6))
    df.boxplot(column='yield_tons', by='crop_name', figsize=(12, 6))
    plt.xlabel('Crop Type')
    plt.ylabel('Yield (tons)')
    plt.title('Yield Distribution by Crop Type')
    plt.suptitle('')  # Remove default title
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('yield_by_crop.png', dpi=150)
    print("✓ Saved 'yield_by_crop.png'")
    plt.close()
    
    print("\nVisualization complete!")

def main():
    """
    Main training pipeline
    """
    print("\n" + "="*60)
    print(" CROP YIELD PREDICTION - ML MODEL TRAINING ")
    print("="*60)
    
    # Generate data
    df = generate_synthetic_crop_data(n_samples=2000)
    
    # Save dataset
    df.to_csv('training_data.csv', index=False)
    print(f"\n✓ Training data saved as 'training_data.csv'")
    
    # Train model
    model, encoders, feature_cols, X_test, y_test, y_pred_test = train_model(df)
    
    # Save model
    save_model(model, encoders, feature_cols)
    
    # Create visualizations
    create_visualizations(df, X_test, y_test, y_pred_test)
    
    print("\n" + "="*60)
    print(" TRAINING COMPLETE! ")
    print("="*60)
    print("\nGenerated files:")
    print("  1. model.pkl - Trained Random Forest model")
    print("  2. encoders.pkl - Label encoders for categorical features")
    print("  3. feature_cols.pkl - Feature column names")
    print("  4. training_data.csv - Synthetic training dataset")
    print("  5. prediction_accuracy.png - Visualization")
    print("  6. yield_by_crop.png - Crop yield distribution")
    print("\nYou can now use this model in your Flask app!")
    print("The model will make real predictions based on trained data.")

if __name__ == "__main__":
    main()