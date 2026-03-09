import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.svm import SVC

def create_initial_models():
    print("🧠 Starting initial model training...")
    
    # 1. Create Synthetic Data (100 rows of sensor readings)
    # Features: [temp, hum, pres, gas, co, dust]
    X_train = np.random.rand(100, 6) 
    
    # 2. Train Regression Model (Predicting AQI)
    # Dummy target: AQI values between 0.0 and 1.0
    y_reg = np.random.rand(100)
    reg_model = RandomForestRegressor(n_estimators=10).fit(X_train, y_reg)
    joblib.dump(reg_model, 'reg_model.pkl')
    print("✅ Created: reg_model.pkl")
    
    # 3. Train Classification Model (Health States)
    # 0: Healthy, 1: Warning, 2: Hazardous
    y_class = np.random.randint(0, 3, 100)
    clf_model = SVC(probability=True).fit(X_train, y_class)
    joblib.dump(clf_model, 'clf_model.pkl')
    print("✅ Created: clf_model.pkl")
    
    # 4. Train Anomaly Detection (Isolation Forest)
    # contamination=0.1 means we expect 10% of data to be outliers
    iso_forest = IsolationForest(contamination=0.1, random_state=42).fit(X_train)
    joblib.dump(iso_forest, 'anomaly_model.pkl')
    print("✅ Created: anomaly_model.pkl")

    print("\n🚀 All models generated! You can now run server.py")

if __name__ == "__main__":
    create_initial_models()