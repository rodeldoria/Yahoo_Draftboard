import logging
from flask import Flask, jsonify, request, render_template
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League

app = Flask(__name__)

# Initialize OAuth2
oauth = OAuth2(None, None, from_file='oauth2.json')

# Check if the token is valid, refresh if necessary
if not oauth.token_is_valid():
    oauth.refresh_access_token()

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/drafts/<league_key>', methods=['GET'])
def get_draft_results_by_key(league_key):
    """Get draft results by league key and include player details."""
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

        # Extract player IDs from draft results
        player_ids = [result['player_id'] for result in draft_results]

        # Fetch player details for each player ID
        player_details = league.player_details(player_ids)

        # Create a dictionary for quick lookup of player details by player_id
        player_details_dict = {player['player_id']: player for player in player_details}

        # Combine draft results with player details
        for result in draft_results:
            player_id = result['player_id']
            if player_id in player_details_dict:
                player_info = player_details_dict[player_id]
                result['player_name'] = player_info['name']['full']
                result['image_url'] = player_info.get('image_url', '')
                result['display_position'] = player_info.get('display_position', '')
                result['editorial_team_abbr'] = player_info.get('editorial_team_abbr', '')

        return jsonify(draft_results)
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-details', methods=['GET'])
def get_player_details():
    """Get player details."""
    try:
        league_id = request.args.get('league_id')
        player_identifier = request.args.get('player')  # Either player ID or search term

        if not player_identifier:
            raise ValueError("Player identifier is required")

        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)

        if player_identifier.isdigit():
            # If the player identifier is a digit, assume it's a player ID
            player_details = league.player_details(int(player_identifier))
        else:
            # Otherwise, search by name
            player_details = league.player_details(player_identifier)

        # Format response to match your desired structure
        formatted_details = []
        for player in player_details:
            formatted_details.append({
                "player_id": player["player_id"],
                "name": player["name"],
                "editorial_team_abbr": player["editorial_team_abbr"],
                "display_position": player["display_position"],
                "image_url": player.get("image_url", "")
            })

        return jsonify({"details": formatted_details})
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)