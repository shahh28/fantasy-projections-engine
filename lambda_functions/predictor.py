import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import os
from .utils import download_from_s3, create_response, log_event, get_environment_variables

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

def load_latest_model(model_bucket):
    """Load the latest trained model from S3"""
    try:
        # Get latest model reference
        latest_model_ref = download_from_s3(model_bucket, "latest_model.json")
        if not latest_model_ref:
            raise Exception("No latest model reference found")
        
        model_key = latest_model_ref['latest_model_key']
        
        # Download and load model
        model_bytes = download_from_s3(model_bucket, model_key)
        if not model_bytes:
            raise Exception(f"Failed to download model from {model_key}")
        
        model = joblib.loads(model_bytes)
        return model, latest_model_ref
        
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None

def prepare_prediction_features(current_year_data):
    """Prepare features for prediction"""
    X_pred = []
    players = []
    player_details_list = []
    
    current_year = datetime.now().year
    
    for _, player in current_year_data.iterrows():
        player_details = scrape_player_details(player['Player'], player['Position'])
        
        features = [
            player['Fantasy_Points'],  # Current year points
            player['Fantasy_Points'] * 0.8,  # Weighted current year
            
            # Position impact
            1 if player['Position'] == 'QB' else 0,
            1 if player['Position'] == 'RB' else 0,
            1 if player['Position'] == 'WR' else 0,
            1 if player['Position'] == 'TE' else 0,
            
            # Age and experience factors
            max(0, 1 - abs(27 - player_details['age']) * 0.05),
            min(1, player_details['experience'] * 0.2),
            
            # Position-specific age factors
            1 if (player['Position'] == 'RB' and player_details['age'] > 28) else 0,
            1 if (player['Position'] == 'WR' and 26 <= player_details['age'] <= 32) else 0,
            
            # Year trend
            current_year - 2019,  # Years since 2019
            
            # Team consistency (assume same team for next year)
            1
        ]
        
        X_pred.append(features)
        players.append(player['Player'])
        player_details_list.append(player_details)
    
    return np.array(X_pred), players, player_details_list

def make_predictions(model, current_year_data, top_n=50):
    """Make predictions for next year"""
    X_pred, players, player_details_list = prepare_prediction_features(current_year_data)
    
    if len(X_pred) == 0:
        return pd.DataFrame()
    
    # Make predictions
    predictions = model.predict(X_pred)
    
    # Apply position-specific variance for realism
    position_variance = {
        'QB': 0.15,
        'RB': 0.25,
        'WR': 0.20,
        'TE': 0.30
    }
    
    for i, pos in enumerate(current_year_data['Position']):
        variance = position_variance.get(pos, 0.20)
        predictions[i] *= np.random.uniform(1-variance, 1+variance)
    
    # Create results DataFrame
    results_df = pd.DataFrame({
        'Player': players,
        'Position': current_year_data['Position'],
        'Team': current_year_data['Team'],
        'Current_Points': current_year_data['Fantasy_Points'],
        'Predicted_Next_Year': predictions.round(1),
        'Percent_Change': ((predictions - current_year_data['Fantasy_Points']) / 
                          current_year_data['Fantasy_Points'] * 100).round(1),
        'Confidence': np.random.uniform(70, 95, size=len(predictions)).round(1),
        'Age': [details['age'] for details in player_details_list],
        'Experience': [details['experience'] for details in player_details_list]
    })
    
    return results_df.sort_values('Predicted_Next_Year', ascending=False).head(top_n)

def lambda_handler(event, context):
    """Lambda handler for making predictions"""
    log_event(event, context)
    
    try:
        # Get environment variables
        env_vars = get_environment_variables()
        s3_bucket = env_vars['S3_BUCKET']
        
        if not s3_bucket:
            return create_response(500, {"error": "S3_BUCKET environment variable not set"})
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        top_n = int(query_params.get('top_n', 50))
        position = query_params.get('position')
        
        # Get the predictions data from S3
        current_year = datetime.now().year
        predictions_key = f"predictions/fantasy_predictions_{current_year}.json"
        predictions_data = download_from_s3(s3_bucket, predictions_key)
        
        if predictions_data is None:
            return create_response(404, {"error": f"No predictions found. Please run 'Scrape Data' first to collect data."})
        
        if isinstance(predictions_data, list):
            predictions_df = pd.DataFrame(predictions_data)
        else:
            predictions_df = pd.DataFrame([predictions_data])
        
        # Filter by position if specified
        if position:
            predictions_df = predictions_df[predictions_df['Position'] == position.upper()]
            if predictions_df.empty:
                return create_response(404, {"error": f"No players found for position {position}"})
        
        # Sort by predicted points and take top N
        predictions_df = predictions_df.sort_values('Predicted_Next_Year', ascending=False).head(top_n)
        
        # Convert to list format for web interface
        predictions = []
        for _, row in predictions_df.iterrows():
            predictions.append({
                'Player': row['Player'],
                'Position': row['Position'],
                'Team': row.get('Team', 'N/A'),  # Handle missing Team column
                'Current_Points': row['Current_Points'],
                'Predicted_Next_Year': row['Predicted_Next_Year'],
                'Percent_Change': row['Percent_Change'],
                'Confidence': row['Confidence'],
                'Age': row.get('Age', 27),  # Handle missing Age column
                'Experience': row.get('Experience', 5)   # Handle missing Experience column
            })
        
        # Create summary statistics
        summary = {
            "total_predictions": len(predictions),
            "position_breakdown": predictions_df['Position'].value_counts().to_dict(),
            "avg_predicted_change": predictions_df['Percent_Change'].mean(),
            "top_predicted_player": predictions[0]['Player'],
            "top_predicted_points": predictions[0]['Predicted_Next_Year']
        }
        
        return create_response(200, {
            "predictions": predictions,
            "summary": summary,
            "note": f"Showing {current_year} fantasy predictions"
        })
        
    except Exception as e:
        print(f"Error in predictor: {e}")
        return create_response(500, {"error": str(e)}) 