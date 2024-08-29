import logging
from flask import Flask, jsonify, request, render_template
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League
import pandas as pd  # Add this import at the top
import os
import requests
import pdfplumber
import re

app = Flask(__name__)
SLEEPER_API_BASE = "https://api.sleeper.app/v1"

# Initialize OAuth2
oauth = OAuth2(None, None, from_file='oauth2.json')

# Check if the token is valid, refresh if necessary
if not oauth.token_is_valid():
    oauth.refresh_access_token()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to fetch draft data from the Sleeper API
def fetch_draft_data(draft_id):
    url = f"{SLEEPER_API_BASE}/draft/{draft_id}/picks"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        app.logger.debug(f"Draft data fetched successfully: {response.json()}")
        return response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error fetching draft data: {e}")
        return None

# Function to read CSV data and clean up headers and data
def read_csv_data(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()  # Strip whitespace from headers
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)  # Strip whitespace from data
    return df

# Function to normalize player names by trimming whitespace and removing suffixes
def normalize_player_name(name):
    """Normalize player names by trimming whitespace and removing suffixes."""
    name = name.strip()
    suffixes = ["Sr.", "Jr.", "II", "III", "IV"]
    parts = name.split()
    if parts[-1] in suffixes:
        name = " ".join(parts[:-1])
    return name

# Function to extract player data from a PDF file
def extract_data_from_pdf(pdf_path):
    player_data = {
        "QB": [],
        "RB": [],
        "WR": [],
        "TE": [],
        "DEF": [],
        "K": []
    }
    
    current_position = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    print("No text found on this page.")
                    continue
                
                lines = text.split("\n")
                
                for line in lines:
                    print(f"Processing line: {line}")  # Debugging line
                    
                    # Identify position groups
                    if "Quarterbacks" in line:
                        current_position = "QB"
                        continue
                    elif "Running Backs" in line:
                        current_position = "RB"
                        continue
                    elif "Wide Receivers" in line:
                        current_position = "WR"
                        continue
                    elif "Tight Ends" in line:
                        current_position = "TE"
                        continue
                    elif "Defenses" in line:
                        current_position = "DEF"
                        continue
                    elif "Kickers" in line:
                        current_position = "K"
                        continue
                    
                    # Match player data including rank, team, and ADP
                    player_match = re.match(r'(\d+)\s+([\w\s\'\-\.]+)\s*\(?(\w+)?\)?\s*([\d\.]+)?', line)
                    if player_match:
                        rank = int(player_match.group(1))
                        name = normalize_player_name(player_match.group(2))
                        team = player_match.group(3) if player_match.group(3) else "N/A"  # Default to N/A if team is missing
                        adp = player_match.group(4) if player_match.group(4) else "N/A"  # Default to N/A if ADP is missing
                        
                        # Append player data based on position
                        if current_position in player_data:
                            player_data[current_position].append({
                                "Rank": rank,
                                "Name": name,
                                "Team": team,
                                "ADP": adp,
                                "ID": fetch_player_id(name)  # Fetch player ID for image
                            })
    
    except Exception as e:
        print(f"Error processing PDF: {e}")  # Debugging line
    
    return player_data

# Function to fetch player ID from the Sleeper API based on player name
def fetch_player_id(player_name):
    """Fetch player ID from the Sleeper API based on player name"""
    normalized_name = normalize_player_name(player_name)
    url = f"{SLEEPER_API_BASE}/search/players"
    params = {"query": normalized_name}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]["player_id"]
    return None

# Route for the main index page
@app.route('/')
def index():
    return render_template('index.html')

# API route to get draft picks for a specific draft ID
@app.route('/api/draft/<draft_id>/picks', methods=['GET'])
def get_draft_picks(draft_id):
    data = fetch_draft_data(draft_id)
    if data is not None:
        return jsonify(data)
    else:
        return jsonify({"error": "Unable to fetch draft picks"}), 500

# API route to get draft data as a DataFrame
@app.route('/api/draft/<draft_id>/dataframe', methods=['GET'])
def get_draft_dataframe(draft_id):
    data = fetch_draft_data(draft_id)
    if data is not None:
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()  # Strip whitespace from headers
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)  # Strip whitespace from data
        return df.to_json(orient='records')
    else:
        return jsonify({"error": "Unable to fetch draft picks"}), 500

# API route to upload a file (CSV or PDF) and process it
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and (file.filename.endswith('.csv') or file.filename.endswith('.pdf')):
        file_path = f"./uploads/{file.filename}"
        file.save(file_path)
        
        if file.filename.endswith('.csv'):
            data = read_csv_data(file_path)
            players = data.to_dict(orient='records')
        else:
            player_data = extract_data_from_pdf(file_path)
            players = player_data
        
        os.remove(file_path)  # Clean up the uploaded file
        return jsonify(players)
    else:
        return jsonify({"error": "Invalid file type"}), 400

# API route to get draft players based on draft ID
@app.route('/api/draft_players', methods=['GET'])
def get_draft_players():
    try:
        # Fetch draft data (replace with actual draft ID)
        draft_id = request.args.get('draft_id', 'your_draft_id_here')
        draft_data = fetch_draft_data(draft_id)
        if draft_data is None:
            return jsonify({"error": "Unable to fetch draft picks"}), 500

        # Fetch all NFL players (this is a large request, consider caching)
        all_players_response = requests.get(f"{SLEEPER_API_BASE}/players/nfl")
        all_players_response.raise_for_status()
        all_players = all_players_response.json()

        player_details = []
        for pick in draft_data:
            player_id = pick['player_id']
            player_info = all_players.get(player_id, {})

            player_details.append({
                'full_name': player_info.get('full_name', 'Unknown'),
                'position': player_info.get('position', 'Unknown'),
                'team': player_info.get('team', 'Unknown'),
                'pick_no': pick['pick_no'],
                'round': pick['round'],
                'draft_slot': pick['draft_slot'],
                'image_url': f'https://sleepercdn.com/content/nfl/players/{player_id}.jpg',
                'player_id': player_id
            })

        return jsonify(player_details)

    except requests.RequestException as e:
        app.logger.error(f"Failed to fetch data: {e}")
        return jsonify({"error": f"Failed to fetch data: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": f"Error processing request: {e}"}), 500

# API route to search for players based on a query
@app.route('/api/search_players', methods=['GET'])
def search_players():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Fetch players from the Sleeper API
    url = f"{SLEEPER_API_BASE}/search/players"
    params = {"query": query}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch players"}), 500

# Route for team logo upload and display
@app.route('/team_logo', methods=['GET', 'POST'])  # New route for team logo
def team_logo():
    logo_url = None
    if request.method == 'POST':
        team_name = request.form.get('team_name')  # Change to team_name
        logo_url = f"https://sleepercdn.com/images/team_logos/nfl/{team_name}.png"  # Use team_name
    return render_template("draft_tiers.html", logo_url=logo_url)

# Main entry point to run the Flask application
if __name__ == '__main__':
    os.makedirs('./uploads', exist_ok=True)  # Create uploads directory if it doesn't exist
    logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG
    app.run(debug=True)  # Run the Flask app in debug mode