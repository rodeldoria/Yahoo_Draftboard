from flask import Flask, jsonify, request, render_template
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League
import json
import logging

app = Flask(__name__)

# Initialize OAuth2
oauth = OAuth2(None, None, from_file='oauth2.json')

# Check if the token is valid, refresh if necessary
if not oauth.token_is_valid():
    oauth.refresh_access_token()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/league', methods=['GET'])
def get_league_details():
    """Get league details."""
    try:
        league_id = request.args.get('league_id')
        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)
        league_details = league.settings()
        return jsonify(league_details)
    except Exception as e:
        logging.error(f"Error fetching league details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/drafts/<league_key>', methods=['GET'])
def get_draft_results_by_key(league_key):
    """Get draft results by league key."""
    try:
        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_key)
        draft_results = league.draft_results()
        if not draft_results:
            return jsonify({"message": "No draft results available."}), 404
        return jsonify(draft_results)
    except Exception as e:
        logging.error(f"Error fetching draft results: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/standings', methods=['GET'])
def get_standings():
    """Get league standings."""
    try:
        league_id = request.args.get('league_id')
        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)
        standings = league.standings()
        return jsonify(standings)
    except Exception as e:
        logging.error(f"Error fetching standings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teams', methods=['GET'])
def get_all_teams():
    """Get all teams."""
    try:
        league_id = request.args.get('league_id')
        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)
        teams = league.teams()
        return jsonify(teams)
    except Exception as e:
        logging.error(f"Error fetching teams: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teams/<league_id>', methods=['GET'])
def get_teams_by_league(league_id):
    """Get team details by league ID."""
    try:
        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)
        teams = league.teams()
        return jsonify(teams)
    except Exception as e:
        logging.error(f"Error fetching teams: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/players/<player_id>', methods=['GET'])
def get_player_details(player_id):
    """Get player details."""
    try:
        league_id = request.args.get('league_id')
        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)
        player_details = league.player_details(player_id)
        return jsonify(player_details)
    except Exception as e:
        logging.error(f"Error fetching player details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/player-details', methods=['GET'])
def get_player_details_from_json():
    """Get player details from JSON file."""
    try:
        with open('harambot/tests/test-player-details.json') as f:
            player_data = json.load(f)
        return jsonify(player_data)
    except Exception as e:
        logging.error(f"Error fetching player details from JSON: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_draft_results', methods=['POST'])
def fetch_draft_results():
    league_id = request.json.get('league_id')
    nfl_game = Game(oauth, 'nfl')

    try:
        league = nfl_game.to_league(league_id)
        draft_results = league.draft_results()

        # Print draft results to the console
        logging.debug(f"Draft Results: {draft_results}")

        # Prepare draft results information
        draft_info_list = []
        for result in draft_results:
            player_info = league.player_details(result['player_id'])[0]
            player_stats = league.player_stats([result['player_id']], 'season', season=2022)  # Fetch stats for the last season
            draft_info = {
                'pick': result['pick'],
                'round': result['round'],
                'team_key': result['team_key'],
                'player_id': result['player_id'],
                'player_name': player_info['name']['full'],
                'position': player_info['primary_position'],
                'stats': player_stats
            }
            draft_info_list.append(draft_info)

        return jsonify({'draft_results': draft_info_list})
    except RuntimeError as e:
        error_message = str(e)
        logging.error(f"Runtime error: {error_message}")
        if "Player key" in error_message and "does not exist" in error_message:
            return jsonify({'error': 'One or more player keys do not exist. Please check the player IDs and try again.'})
        return jsonify({'error': error_message})
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)