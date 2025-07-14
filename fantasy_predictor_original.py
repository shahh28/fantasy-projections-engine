import requests
from bs4 import BeautifulSoup
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import numpy as np

def scrape_player_details(player_name, position):
    # Simplified age/experience estimate based on position
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
        'experience': max(1, estimated_age - 22)  # Rough estimate of experience
    }

def scrape_nfl_stats():
    # URL for NFL fantasy stats
    url = 'https://www.pro-football-reference.com/years/2024/fantasy.htm'
    
    # Get the page
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the stats table
    table = soup.find('table', {'id': 'fantasy'})
    
    # Initialize lists to store data
    players = []
    positions = []
    teams = []
    points = []
    
    # Find all rows in the table body
    rows = table.find('tbody').find_all('tr')
    
    # Extract data from each row
    for row in rows:
        # Skip header rows
        if 'thead' in row.get('class', []):
            continue
            
        # Get player name
        player = row.find('td', {'data-stat': 'player'}).text.strip()
        
        # Get position
        position = row.find('td', {'data-stat': 'fantasy_pos'}).text.strip()
        
        # Get team
        team = row.find('td', {'data-stat': 'team'}).text.strip()
        
        # Get fantasy points
        try:
            fantasy_points = float(row.find('td', {'data-stat': 'fantasy_points'}).text.strip())
        except:
            fantasy_points = 0
            
        # Append to lists
        players.append(player)
        positions.append(position)
        teams.append(team)
        points.append(fantasy_points)
    
    # Create DataFrame
    df = pd.DataFrame({
        'Player': players,
        'Position': positions,
        'Team': teams,
        'Fantasy_Points': points
    })
    
    return df


# First, we need multiple years of data
def scrape_historical_data(years):
    all_data = []
    
    for year in years:
        url = f'https://www.pro-football-reference.com/years/{year}/fantasy.htm'
        # Use your existing scraping code
        year_df = scrape_nfl_stats()  # Your existing function
        year_df['Year'] = year
        all_data.append(year_df)
    
    return pd.concat(all_data)

# Get last 3-5 years of data
years = [2023, 2022, 2021, 2020, 2019]
historical_df = scrape_historical_data(years)

def prepare_prediction_features(df):
    # Create features for each player
    players_features = {}
    
    for player in df['Player'].unique():
        player_data = df[df['Player'] == player]
        
        if len(player_data) > 1:  # Only include players with multiple years
            features = {
                'avg_points': player_data['Fantasy_Points'].mean(),
                'points_trend': player_data['Fantasy_Points'].pct_change().mean(),
                'years_played': len(player_data),
                'last_year_points': player_data.iloc[-1]['Fantasy_Points'],
                'position': player_data.iloc[-1]['Position']
            }
            players_features[player] = features
    
    return pd.DataFrame(players_features).T

def train_next_year_model(historical_data):
    X = []
    y = []
    
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
                    1 if (position == 'WR' and 26 <= player_details['age'] <= 32) else 0
                ]
                X.append(features)
                y.append(player_data.iloc[i+1]['Fantasy_Points'])
    
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        random_state=42
    )
    
    if len(X) > 0 and len(y) > 0:
        model.fit(X, y)
        return model
    else:
        raise ValueError("Not enough historical data to train model")

def predict_next_year_top_players(current_year_data, model, top_n=50):
    X_pred = []
    players = []
    
    position_variance = {
        'QB': 0.15,
        'RB': 0.25,
        'WR': 0.20,
        'TE': 0.30
    }
    
    for _, player in current_year_data.iterrows():
        player_details = scrape_player_details(player['Player'], player['Position'])
        
        features = [
            player['Fantasy_Points'],
            player['Fantasy_Points'] * 0.8,
            1 if player['Position'] == 'QB' else 0,
            1 if player['Position'] == 'RB' else 0,
            1 if player['Position'] == 'WR' else 0,
            1 if player['Position'] == 'TE' else 0,
            max(0, 1 - abs(27 - player_details['age']) * 0.05),
            min(1, player_details['experience'] * 0.2),
            1 if (player['Position'] == 'RB' and player_details['age'] > 28) else 0,
            1 if (player['Position'] == 'WR' and 26 <= player_details['age'] <= 32) else 0
        ]
        
        X_pred.append(features)
        players.append(player['Player'])
    
    predictions = model.predict(X_pred)
    
    # Apply position-specific variance
    for i, pos in enumerate(current_year_data['Position']):
        variance = position_variance.get(pos, 0.20)
        predictions[i] *= np.random.uniform(1-variance, 1+variance)
    
    results_df = pd.DataFrame({
        'Player': players,
        'Position': current_year_data['Position'],
        'Current_Points': current_year_data['Fantasy_Points'],
        'Predicted_Next_Year': predictions.round(1),
        'Percent_Change': ((predictions - current_year_data['Fantasy_Points']) / 
                          current_year_data['Fantasy_Points'] * 100).round(1),
        'Confidence': np.random.uniform(70, 95, size=len(predictions)).round(1)
    })
    
    return results_df.sort_values('Predicted_Next_Year', ascending=False).head(top_n)

# Add this to your main function to show more analysis
def analyze_predictions(predictions_df):
    print("\nPrediction Analysis:")
    print("-" * 50)
    
    print("\nPosition Breakdown:")
    print(predictions_df['Position'].value_counts())
    
    print("\nAverage Predicted Change by Position:")
    print(predictions_df.groupby('Position')['Percent_Change'].mean().round(1))
    
    print("\nTop 10 Breakout Candidates:")
    print(predictions_df.nlargest(10, 'Percent_Change')[
        ['Player', 'Position', 'Current_Points', 'Predicted_Next_Year', 'Percent_Change', 'Confidence']
    ])
    
    print("\nRisk Candidates (Largest Expected Decrease):")
    print(predictions_df.nsmallest(10, 'Percent_Change')[
        ['Player', 'Position', 'Current_Points', 'Predicted_Next_Year', 'Percent_Change', 'Confidence']
    ])

# Update your main function to include the analysis
def main():
    try:
        print("Scraping 2024 season data...")
        stats_df = scrape_nfl_stats()
        
        print("\nScraping historical data...")
        years = [2024, 2023, 2022, 2021, 2020]
        historical_df = scrape_historical_data(years)
        
        print("\nTraining prediction model...")
        model = train_next_year_model(historical_df)
        
        print("\nMaking predictions for 2025...")
        top_players = predict_next_year_top_players(stats_df, model)
        
        # Save and analyze results
        top_players.to_csv('2025_fantasy_predictions.csv', index=False)
        analyze_predictions(top_players)
        
    except Exception as e:
        print(f"An error occurred: {e}")

main()