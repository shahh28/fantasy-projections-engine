import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from datetime import datetime
import os
from .utils import upload_to_s3, download_from_s3, create_response, log_event, get_environment_variables

def scrape_player_details(player_name, position):
    """Estimate player age and experience based on position"""
    age_ranges = {
        'QB': (25, 35),
        'RB': (22, 28),
        'WR': (23, 30),
        'TE': (23, 29)
    }
    default_range = age_ranges.get(position, (24, 29))
    estimated_age = np.random.randint(default_range[0], default_range[1])
    
    return {
        'age': estimated_age,
        'experience': max(1, estimated_age - 22)
    }

def prepare_training_data(historical_data):
    """Prepare training data from historical fantasy stats"""
    X = []
    y = []
    player_info = []
    
    for player in historical_data['Player'].unique():
        player_data = historical_data[historical_data['Player'] == player].sort_values('Year')
        
        if len(player_data) >= 2:
            position = player_data.iloc[-1]['Position']
            player_details = scrape_player_details(player, position)
            
            for i in range(len(player_data)-1):
                # Enhanced features
                features = [
                    player_data.iloc[i]['Fantasy_Points'],  # Current year points
                    player_data.iloc[i]['Fantasy_Points'] * 0.8,  # Weighted current year
                    
                    # Position impact
                    1 if position == 'QB' else 0,
                    1 if position == 'RB' else 0,
                    1 if position == 'WR' else 0,
                    1 if position == 'TE' else 0,
                    
                    # Age and experience factors
                    max(0, 1 - abs(27 - player_details['age']) * 0.05),
                    min(1, player_details['experience'] * 0.2),
                    
                    # Position-specific age factors
                    1 if (position == 'RB' and player_details['age'] > 28) else 0,
                    1 if (position == 'WR' and 26 <= player_details['age'] <= 32) else 0,
                    
                    # Year trend
                    player_data.iloc[i]['Year'] - 2019,  # Years since 2019
                    
                    # Team consistency (simplified)
                    1 if player_data.iloc[i]['Team'] == player_data.iloc[i+1]['Team'] else 0
                ]
                
                X.append(features)
                y.append(player_data.iloc[i+1]['Fantasy_Points'])
                player_info.append({
                    'player': player,
                    'position': position,
                    'current_year': player_data.iloc[i]['Year'],
                    'next_year': player_data.iloc[i+1]['Year']
                })
    
    return np.array(X), np.array(y), player_info

def train_model(X, y):
    """Train Random Forest model"""
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    # Feature importance
    feature_names = [
        'current_points', 'weighted_points', 'qb', 'rb', 'wr', 'te',
        'age_factor', 'experience_factor', 'rb_age_risk', 'wr_age_peak',
        'years_since_2019', 'team_consistency'
    ]
    
    feature_importance = dict(zip(feature_names, model.feature_importances_))
    
    return {
        'model': model,
        'metrics': {
            'mse': mse,
            'rmse': np.sqrt(mse),
            'r2': r2,
            'feature_importance': feature_importance
        },
        'test_predictions': {
            'y_test': y_test.tolist(),
            'y_pred': y_pred.tolist()
        }
    }

def lambda_handler(event, context):
    """Lambda handler for model training"""
    log_event(event, context)
    
    try:
        # Get environment variables
        env_vars = get_environment_variables()
        s3_bucket = env_vars['S3_BUCKET']
        model_bucket = env_vars['MODEL_BUCKET']
        
        if not s3_bucket or not model_bucket:
            return create_response(500, {"error": "S3_BUCKET or MODEL_BUCKET environment variable not set"})
        
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON in request body"})
        
        # Get data source (default to latest raw data)
        data_source = body.get('data_source', 'latest')
        
        # Download training data from S3
        if data_source == 'latest':
            # Find the latest raw data file
            from .utils import list_s3_objects
            raw_data_files = list_s3_objects(s3_bucket, 'raw_data/')
            if not raw_data_files:
                return create_response(500, {"error": "No raw data found in S3"})
            
            latest_file = sorted(raw_data_files)[-1]
            historical_data = download_from_s3(s3_bucket, latest_file)
        else:
            # Use specific data source
            historical_data = download_from_s3(s3_bucket, data_source)
        
        if historical_data is None:
            return create_response(500, {"error": "Failed to download training data from S3"})
        
        # Convert to DataFrame if it's a list
        if isinstance(historical_data, list):
            historical_data = pd.DataFrame(historical_data)
        
        print(f"Training model with {len(historical_data)} records")
        
        # Prepare training data
        X, y, player_info = prepare_training_data(historical_data)
        
        if len(X) == 0:
            return create_response(500, {"error": "No valid training data found"})
        
        print(f"Prepared {len(X)} training samples")
        
        # Train model
        training_result = train_model(X, y)
        model = training_result['model']
        metrics = training_result['metrics']
        
        # Save model to S3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_key = f"models/fantasy_predictor_{timestamp}.joblib"
        
        # Serialize model
        model_bytes = joblib.dumps(model)
        upload_to_s3(model_bytes, model_bucket, model_key, 'application/octet-stream')
        
        # Save model metadata
        metadata = {
            "timestamp": timestamp,
            "model_type": "RandomForestRegressor",
            "training_samples": len(X),
            "features": len(X[0]),
            "metrics": metrics,
            "model_key": model_key,
            "data_source": data_source,
            "player_info_sample": player_info[:10]  # Sample of player info
        }
        
        metadata_key = f"metadata/model_metadata_{timestamp}.json"
        upload_to_s3(metadata, model_bucket, metadata_key)
        
        # Save latest model reference
        latest_model_ref = {
            "latest_model_key": model_key,
            "latest_metadata_key": metadata_key,
            "last_updated": timestamp
        }
        
        upload_to_s3(latest_model_ref, model_bucket, "latest_model.json")
        
        return create_response(200, {
            "message": "Model training completed successfully",
            "model_info": {
                "model_key": model_key,
                "metadata_key": metadata_key,
                "training_samples": len(X),
                "metrics": metrics
            }
        })
        
    except Exception as e:
        print(f"Error in model trainer: {e}")
        return create_response(500, {"error": str(e)}) 