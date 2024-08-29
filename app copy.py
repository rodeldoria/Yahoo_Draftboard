import logging
from flask import Flask, jsonify, request, render_template
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League
import pandas as pd
import pdfplumber
import os
import re
from werkzeug.utils import secure_filename
from requests.exceptions import RequestException

app = Flask(__name__)

# Initialize OAuth2
oauth = OAuth2(None, None, from_file='oauth2.json')

# Check if the token is valid, refresh if necessary
if not oauth.token_is_valid():
    oauth.refresh_access_token()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Functions from Tiers.py
def normalize_player_name(name):
    """Normalize player names by trimming whitespace and removing suffixes."""
    name = name.strip()
    suffixes = ["Sr.", "Jr.", "II", "III", "IV"]
    parts = name.split()
    if parts[-1] in suffixes:
        name = " ".join(parts[:-1])
    return name

def read_csv_data(file_path):
    """Read CSV data and clean up headers and data."""
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df

def extract_data_from_pdf(pdf_path):
    """Extract player data from a PDF file."""
    player_data = {
        "QB": [], "RB": [], "WR": [], "TE": [], "DEF": [], "K": []
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
                    print(f"Processing line: {line}")
                    
                    if "Quarterbacks" in line:
                        current_position = "QB"
                    elif "Running Backs" in line:
                        current_position = "RB"
                    elif "Wide Receivers" in line:
                        current_position = "WR"
                    elif "Tight Ends" in line:
                        current_position = "TE"
                    elif "Defenses" in line:
                        current_position = "DEF"
                    elif "Kickers" in line:
                        current_position = "K"
                    else:
                        player_match = re.match(r'(\d+)\s+([\w\s\'\-\.]+)\s*\(?(\w+)?\)?\s*([\d\.]+)?', line)
                        if player_match and current_position in player_data:
                            rank = int(player_match.group(1))
                            name = normalize_player_name(player_match.group(2))
                            team = player_match.group(3) or "N/A"
                            adp = player_match.group(4) or "N/A"
                            
                            player_data[current_position].append({
                                "Rank": rank,
                                "Name": name,
                                "Team": team,
                                "ADP": adp,
                            })
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
    
    return player_data

def process_uploaded_file(file_path):
    """Process an uploaded file (CSV or PDF) and return player data."""
    if file_path.endswith('.csv'):
        data = read_csv_data(file_path)
        return data.to_dict(orient='records')
    elif file_path.endswith('.pdf'):
        return extract_data_from_pdf(file_path)
    else:
        raise ValueError("Invalid file type. Only CSV and PDF files are supported.")

def get_team_logo_url(team_name):
    """Get the URL for a team's logo."""
    return f"https://sleepercdn.com/images/team_logos/nfl/{team_name}.png"

def create_upload_directory():
    """Create the uploads directory if it doesn't exist."""
    os.makedirs('./uploads', exist_ok=True)

# Existing routes and functions
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/drafts/<league_key>', methods=['GET'])
def get_draft_results_by_key(league_key):
    try:
        if not oauth.token_is_valid():
            logging.info("Token is not valid, refreshing...")
            oauth.refresh_access_token()
        else:
            logging.info("Token is still valid")

        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_key)
        draft_results = league.draft_results()
        if not draft_results:
            return jsonify({"message": "No draft results available."}), 404

        player_ids = [result['player_id'] for result in draft_results]
        player_details = league.player_details(player_ids)
        player_details_dict = {player['player_id']: player for player in player_details}

        formatted_results = []
        for result in draft_results:
            player_id = result['player_id']
            player_info = player_details_dict.get(player_id, {})
            formatted_result = {
                'pick': result['pick'],
                'round': result['round'],
                'team_key': result['team_key'],
                'player_id': player_id,
                'player_name': player_info.get('name', {}).get('full', ''),
                'position_type': player_info.get('position_type', ''),
                'display_position': player_info.get('display_position', ''),
                'editorial_team_abbr': player_info.get('editorial_team_abbr', ''),
                'headshot_url': player_info.get('headshot', {}).get('url', ''),
            }
            formatted_results.append(formatted_result)

        logging.info(f"Draft results and player details retrieved for {len(formatted_results)} players")
        return jsonify(formatted_results)
    except Exception as e:
        logging.error(f"Exception in get_draft_results_by_key: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-details', methods=['GET'])
def get_player_details():
    """Fetch player details by league ID and player IDs or names."""
    try:
        league_id = request.args.get('league_id')
        player_identifiers = request.args.get('player')

        if not league_id or not player_identifiers:
            return jsonify({'error': 'Missing league_id or player identifiers'}), 400

        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)

        player_identifiers = player_identifiers.split(',')
        player_details = []

        for player_identifier in player_identifiers:
            if player_identifier.isdigit():
                player_details.extend(league.player_details([int(player_identifier)]))
            else:
                player_details.extend(league.player_details(player_identifier))

        if not player_details:
            return jsonify({'message': 'Players not found'}), 404

        formatted_details = []
        ownership = {}
        for player in player_details:
            player_id = player["player_id"]
            formatted_details.append({
                "player_key": player["player_key"],
                "player_id": player_id,
                "name": {
                    "full": player["name"]["full"],
                    "first": player["name"].get("first", ""),
                    "last": player["name"].get("last", ""),
                    "ascii_first": player["name"].get("ascii_first", ""),
                    "ascii_last": player["name"].get("ascii_last", "")
                },
                "editorial_player_key": player.get("editorial_player_key", ""),
                "editorial_team_key": player.get("editorial_team_key", ""),
                "editorial_team_full_name": player.get("editorial_team_full_name", ""),
                "editorial_team_abbr": player.get("editorial_team_abbr", ""),
                "bye_weeks": player.get("bye_weeks", {}),
                "uniform_number": player.get("uniform_number", ""),
                "display_position": player.get("display_position", ""),
                "headshot": {
                    "url": player.get("headshot", {}).get("url", ""),
                    "size": player.get("headshot", {}).get("size", "")
                },
                "image_url": player.get("image_url", ""),
                "is_undroppable": player.get("is_undroppable", ""),
                "position_type": player.get("position_type", ""),
                "primary_position": player.get("primary_position", ""),
                "eligible_positions": player.get("eligible_positions", []),
                "player_stats": player.get("player_stats", {}),
                "player_points": player.get("player_points", {})
            })

            if player_id in ownership:
                ownership[player_id] = {
                    "ownership_type": ownership[player_id].get("ownership_type", ""),
                    "owner_team_name": ownership[player_id].get("owner_team_name", "")
                }

        return jsonify({
            "details": formatted_details,
            "ownership": ownership
        })
    except Exception as e:
        logging.error(f"Exception while fetching player details: {str(e)}")
        return jsonify({'error': str(e)}), 500

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'csv', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        try:
            data = process_uploaded_file(file_path)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    create_upload_directory()
    app.run(debug=True)