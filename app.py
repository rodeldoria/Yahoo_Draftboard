import logging
from flask import Flask, jsonify, request, render_template
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League
import pandas as pd  # Add this import at the top

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

        # Create a DataFrame from draft results
        df_draft_results = pd.DataFrame(draft_results)

        # Add player attributes to the DataFrame
        df_draft_results['player_name'] = df_draft_results['player_id'].map(lambda pid: player_details_dict.get(pid, {}).get('name', {}).get('full', ''))
        df_draft_results['position_type'] = df_draft_results['player_id'].map(lambda pid: player_details_dict.get(pid, {}).get('position_type', ''))

        # Convert DataFrame to JSON for response
        return jsonify(df_draft_results.to_dict(orient='records'))
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-details', methods=['GET'])
def get_player_details():
    """Fetch player details by league ID and player IDs or names."""
    try:
        league_id = request.args.get('league_id')
        player_identifiers = request.args.get('player')  # Comma-separated player IDs or search terms

        if not league_id or not player_identifiers:
            return jsonify({'error': 'Missing league_id or player identifiers'}), 400

        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)

        player_identifiers = player_identifiers.split(',')
        player_details = []

        for player_identifier in player_identifiers:
            if player_identifier.isdigit():
                # If the player identifier is a digit, assume it's a player ID
                player_details.extend(league.player_details([int(player_identifier)]))
            else:
                # Otherwise, search by name
                player_details.extend(league.player_details(player_identifier))

        if not player_details:
            return jsonify({'message': 'Players not found'}), 404

        # Format response to match your desired structure
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

            # Add ownership information if available
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

if __name__ == '__main__':
    app.run(debug=True)