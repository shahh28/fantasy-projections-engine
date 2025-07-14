import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime
import os
from .utils import upload_to_s3, create_response, log_event, get_environment_variables

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

def scrape_nfl_stats(year):
    """Scrape NFL fantasy stats for a specific year"""
    url = f'https://www.pro-football-reference.com/years/{year}/fantasy.htm'
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', {'id': 'fantasy'})
        if not table:
            raise Exception(f"Fantasy stats table not found for year {year}")
        
        players = []
        positions = []
        teams = []
        points = []
        
        rows = table.find('tbody').find_all('tr')
        
        for row in rows:
            if 'thead' in row.get('class', []):
                continue
                
            try:
                player = row.find('td', {'data-stat': 'player'}).text.strip()
                position = row.find('td', {'data-stat': 'fantasy_pos'}).text.strip()
                team = row.find('td', {'data-stat': 'team'}).text.strip()
                
                fantasy_points = 0
                points_cell = row.find('td', {'data-stat': 'fantasy_points'})
                if points_cell:
                    try:
                        fantasy_points = float(points_cell.text.strip())
                    except (ValueError, AttributeError):
                        fantasy_points = 0
                
                players.append(player)
                positions.append(position)
                teams.append(team)
                points.append(fantasy_points)
                
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        df = pd.DataFrame({
            'Player': players,
            'Position': positions,
            'Team': teams,
            'Fantasy_Points': points,
            'Year': year
        })
        
        return df
        
    except Exception as e:
        print(f"Error scraping data for year {year}: {e}")
        return pd.DataFrame()

def scrape_historical_data(years):
    """Scrape historical data for multiple years"""
    all_data = []
    
    for year in years:
        print(f"Scraping data for year {year}...")
        year_df = scrape_nfl_stats(year)
        if not year_df.empty:
            all_data.append(year_df)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()

def lambda_handler(event, context):
    """Lambda handler for data scraping"""
    log_event(event, context)
    
    try:
        # Get environment variables
        env_vars = get_environment_variables()
        s3_bucket = env_vars['S3_BUCKET']
        
        if not s3_bucket:
            return create_response(500, {"error": "S3_BUCKET environment variable not set"})
        
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON in request body"})
        
        # Get years to scrape (default to current year and last 4 years)
        current_year = datetime.now().year
        years = body.get('years', [current_year, current_year-1, current_year-2, current_year-3, current_year-4])
        
        # Scrape data
        print(f"Starting data scrape for years: {years}")
        historical_df = scrape_historical_data(years)
        
        if historical_df.empty:
            return create_response(500, {"error": "No data was scraped successfully"})
        
        # Save to S3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw data
        raw_data_key = f"raw_data/fantasy_stats_{timestamp}.json"
        upload_to_s3(historical_df, s3_bucket, raw_data_key)
        
        # Save current year data separately
        current_year_data = historical_df[historical_df['Year'] == current_year]
        if not current_year_data.empty:
            current_data_key = f"current_year/fantasy_stats_{current_year}.json"
            upload_to_s3(current_year_data, s3_bucket, current_data_key)
        
        # Create summary
        summary = {
            "timestamp": timestamp,
            "years_scraped": years,
            "total_players": len(historical_df),
            "players_by_year": historical_df['Year'].value_counts().to_dict(),
            "players_by_position": historical_df['Position'].value_counts().to_dict(),
            "s3_keys": {
                "raw_data": raw_data_key,
                "current_year": current_data_key if not current_year_data.empty else None
            }
        }
        
        # Save summary
        summary_key = f"summaries/scrape_summary_{timestamp}.json"
        upload_to_s3(summary, s3_bucket, summary_key)
        
        return create_response(200, {
            "message": "Data scraping completed successfully",
            "summary": summary
        })
        
    except Exception as e:
        print(f"Error in data scraper: {e}")
        return create_response(500, {"error": str(e)}) 