import logging
from flask import Flask, jsonify, request, render_template
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League
import aiohttp
from asgiref.sync import async_to_sync

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
                result['editorial_team_full_name'] = player_info.get('editorial_team_full_name', '')
                result['bye_weeks'] = player_info.get('bye_weeks', {})

        return jsonify(draft_results)
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
                "player_key": player["player_key"],
                "player_id": player["player_id"],
                "name": player["name"],
                "editorial_player_key": player["editorial_player_key"],
                "editorial_team_key": player["editorial_team_key"],
                "editorial_team_full_name": player["editorial_team_full_name"],
                "editorial_team_abbr": player["editorial_team_abbr"],
                "bye_weeks": player.get("bye_weeks", {}),
                "uniform_number": player.get("uniform_number", ""),
                "display_position": player.get("display_position", ""),
                "headshot": player.get("headshot", {}),
                "image_url": player.get("image_url", ""),
                "is_undroppable": player.get("is_undroppable", ""),
                "position_type": player.get("position_type", ""),
                "primary_position": player.get("primary_position", ""),
                "eligible_positions": player.get("eligible_positions", []),
                "player_stats": player.get("player_stats", {}),
                "player_points": player.get("player_points", {})
            })

        ownership = league.ownership([player['player_id'] for player in player_details])
        response = {
            "details": formatted_details,
            "ownership": ownership
        }

        return jsonify(response)
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/free-agents', methods=['GET'])
def get_free_agents():
    """Get free agents for a given position."""
    try:
        league_id = request.args.get('league_id')
        position = request.args.get('position')

        nfl_game = Game(oauth, 'nfl')
        league = nfl_game.to_league(league_id)
        free_agents = league.free_agents(position)

        return jsonify(free_agents)
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

async def fetch_player_stats(session, player_ids):
    """Fetch player stats asynchronously."""
    stats = []
    for player_id in player_ids:
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.818153/players;player_keys=nfl.p.{player_id}/stats?format=json"
        async with session.get(url, headers={'Authorization': f'Bearer {oauth.token["access_token"]}'}) as response:
            data = await response.json()
            stats.append(data)
    return stats

@app.route('/get_draft_results', methods=['POST'])
async def fetch_draft_results():
    """Fetch draft results and player stats asynchronously."""
    try:
        draft_results = request.json.get('draft_results', [])
        player_ids = [result['player_id'] for result in draft_results]

        async with aiohttp.ClientSession() as session:
            player_stats = await fetch_player_stats(session, player_ids)

        draft_info_list = []
        for result, stats in zip(draft_results, player_stats):
            player_info = league.player_details(result['player_id'])[0]
            draft_info = {
                'pick': result['pick'],
                'round': result['round'],
                'team_key': result['team_key'],
                'player_id': result['player_id'],
                'player_name': player_info['name']['full'],
                'position': player_info['primary_position'],
                'stats': stats
            }
            draft_info_list.append(draft_info)

        return jsonify({'draft_results': draft_info_list})
    except aiohttp.ClientError as e:
        logging.error(f"Network error: {str(e)}")
        return jsonify({'error': 'Network error. Please try again later.'}), 500
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