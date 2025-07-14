import json
import pandas as pd
import numpy as np
from datetime import datetime
from .utils import download_from_s3, create_response, log_event, get_environment_variables

def analyze_predictions(predictions_df):
    """Analyze prediction results"""
    if predictions_df.empty:
        return {}
    
    analysis = {
        "position_breakdown": predictions_df['Position'].value_counts().to_dict(),
        "avg_predicted_change_by_position": predictions_df.groupby('Position')['Percent_Change'].mean().round(1).to_dict(),
        "top_10_breakout_candidates": predictions_df.nlargest(10, 'Percent_Change')[
            ['Player', 'Position', 'Current_Points', 'Predicted_Next_Year', 'Percent_Change', 'Confidence']
        ].to_dict('records'),
        "risk_candidates": predictions_df.nsmallest(10, 'Percent_Change')[
            ['Player', 'Position', 'Current_Points', 'Predicted_Next_Year', 'Percent_Change', 'Confidence']
        ].to_dict('records'),
        "age_analysis": {
            "avg_age_by_position": predictions_df.groupby('Position')['Age'].mean().round(1).to_dict(),
            "experience_by_position": predictions_df.groupby('Position')['Experience'].mean().round(1).to_dict()
        },
        "confidence_analysis": {
            "avg_confidence": predictions_df['Confidence'].mean().round(1),
            "confidence_by_position": predictions_df.groupby('Position')['Confidence'].mean().round(1).to_dict()
        }
    }
    
    return analysis

def analyze_historical_data(historical_data):
    """Analyze historical fantasy data"""
    if historical_data.empty:
        return {}
    
    analysis = {
        "data_overview": {
            "total_records": len(historical_data),
            "years_covered": sorted(historical_data['Year'].unique()),
            "positions": historical_data['Position'].value_counts().to_dict(),
            "teams": historical_data['Team'].value_counts().head(10).to_dict()
        },
        "points_analysis": {
            "avg_points_by_year": historical_data.groupby('Year')['Fantasy_Points'].mean().round(1).to_dict(),
            "avg_points_by_position": historical_data.groupby('Position')['Fantasy_Points'].mean().round(1).to_dict(),
            "top_scorers_by_year": {}
        },
        "trends": {
            "points_trend_by_position": {}
        }
    }
    
    # Top scorers by year
    for year in historical_data['Year'].unique():
        year_data = historical_data[historical_data['Year'] == year]
        top_scorers = year_data.nlargest(5, 'Fantasy_Points')[
            ['Player', 'Position', 'Team', 'Fantasy_Points']
        ].to_dict('records')
        analysis["points_analysis"]["top_scorers_by_year"][str(year)] = top_scorers
    
    # Points trend by position
    for position in historical_data['Position'].unique():
        pos_data = historical_data[historical_data['Position'] == position]
        trend = pos_data.groupby('Year')['Fantasy_Points'].mean().round(1).to_dict()
        analysis["trends"]["points_trend_by_position"][position] = trend
    
    return analysis

def generate_insights(predictions_df, historical_data):
    """Generate insights from predictions and historical data"""
    insights = []
    
    if not predictions_df.empty:
        # Position insights
        pos_breakdown = predictions_df['Position'].value_counts()
        insights.append(f"Top predictions are dominated by {pos_breakdown.index[0]}s ({pos_breakdown.iloc[0]} players)")
        
        # Breakout insights
        top_breakout = predictions_df.nlargest(1, 'Percent_Change').iloc[0]
        insights.append(f"Biggest breakout candidate: {top_breakout['Player']} ({top_breakout['Position']}) with {top_breakout['Percent_Change']}% increase")
        
        # Risk insights
        top_risk = predictions_df.nsmallest(1, 'Percent_Change').iloc[0]
        insights.append(f"Highest risk player: {top_risk['Player']} ({top_risk['Position']}) with {top_risk['Percent_Change']}% decrease")
        
        # Age insights
        avg_age = predictions_df['Age'].mean()
        insights.append(f"Average age of top predicted players: {avg_age:.1f} years")
    
    if not historical_data.empty:
        # Historical trends
        recent_years = sorted(historical_data['Year'].unique())[-3:]
        if len(recent_years) >= 2:
            recent_data = historical_data[historical_data['Year'].isin(recent_years)]
            avg_points_trend = recent_data.groupby('Year')['Fantasy_Points'].mean()
            if len(avg_points_trend) >= 2:
                trend_direction = "increasing" if avg_points_trend.iloc[-1] > avg_points_trend.iloc[0] else "decreasing"
                insights.append(f"Fantasy points trend is {trend_direction} over the last {len(recent_years)} years")
    
    return insights

def lambda_handler(event, context):
    """Lambda handler for data analysis"""
    log_event(event, context)
    
    try:
        # Get environment variables
        env_vars = get_environment_variables()
        s3_bucket = env_vars['S3_BUCKET']
        model_bucket = env_vars['MODEL_BUCKET']
        
        if not s3_bucket or not model_bucket:
            return create_response(500, {"error": "S3_BUCKET or MODEL_BUCKET environment variable not set"})
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        analysis_type = query_params.get('type', 'all')  # all, predictions, historical, insights
        
        current_year = datetime.now().year
        analysis_results = {}
        
        # Get predictions data if needed
        if analysis_type in ['all', 'predictions', 'insights']:
            try:
                # Get latest predictions
                predictions_key = f"predictions/fantasy_predictions_{current_year}.json"
                predictions_data = download_from_s3(s3_bucket, predictions_key)
                
                if predictions_data:
                    if isinstance(predictions_data, list):
                        predictions_df = pd.DataFrame(predictions_data)
                    else:
                        predictions_df = pd.DataFrame([predictions_data])
                    
                    analysis_results['predictions_analysis'] = analyze_predictions(predictions_df)
                else:
                    analysis_results['predictions_analysis'] = {"error": "No predictions data found"}
            except Exception as e:
                analysis_results['predictions_analysis'] = {"error": f"Failed to analyze predictions: {str(e)}"}
        
        # Get historical data if needed
        if analysis_type in ['all', 'historical', 'insights']:
            try:
                # Get latest historical data
                from .utils import list_s3_objects
                raw_data_files = list_s3_objects(s3_bucket, 'raw_data/')
                
                if raw_data_files:
                    latest_file = sorted(raw_data_files)[-1]
                    historical_data = download_from_s3(s3_bucket, latest_file)
                    
                    if historical_data:
                        if isinstance(historical_data, list):
                            historical_df = pd.DataFrame(historical_data)
                        else:
                            historical_df = pd.DataFrame([historical_data])
                        
                        analysis_results['historical_analysis'] = analyze_historical_data(historical_df)
                    else:
                        analysis_results['historical_analysis'] = {"error": "No historical data found"}
                else:
                    analysis_results['historical_analysis'] = {"error": "No historical data files found"}
            except Exception as e:
                analysis_results['historical_analysis'] = {"error": f"Failed to analyze historical data: {str(e)}"}
        
        # Generate insights if requested
        if analysis_type in ['all', 'insights']:
            try:
                predictions_df = analysis_results.get('predictions_analysis', {}).get('predictions_df', pd.DataFrame())
                historical_df = analysis_results.get('historical_analysis', {}).get('historical_df', pd.DataFrame())
                
                insights = generate_insights(predictions_df, historical_df)
                analysis_results['insights'] = insights
            except Exception as e:
                analysis_results['insights'] = {"error": f"Failed to generate insights: {str(e)}"}
        
        # Add metadata
        analysis_results['metadata'] = {
            "analysis_timestamp": datetime.now().isoformat(),
            "analysis_type": analysis_type,
            "current_year": current_year
        }
        
        return create_response(200, analysis_results)
        
    except Exception as e:
        print(f"Error in analyzer: {e}")
        return create_response(500, {"error": str(e)}) 