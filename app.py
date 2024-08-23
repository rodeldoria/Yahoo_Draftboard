from flask import Flask, render_template, jsonify
import requests
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import game, league

app = Flask(__name__)

# Initialize OAuth2
oauth = OAuth2(None, None, from_file='oauth2.json')

# Create a Game instance for NFL
nfl_game = game.Game(oauth, 'nfl')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/leagues')
def get_leagues():
    league_ids = nfl_game.league_ids()
    return jsonify(league_ids)

@app.route('/api/drafts/<league_id>')
def get_draft_results(league_id):
    lg = league.League(oauth, league_id)
    draft_results = lg.draft_results()

    if draft_results:
        # Extract player IDs from draft results
        player_ids = [result['player_id'] for result in draft_results]
        
        # Fetch player stats for the drafted players
        player_stats = lg.player_stats(player_ids, 'season')  # You can change 'season' to other types if needed

        # Combine draft results with player stats
        for result in draft_results:
            # Find the corresponding player stats
            for stat in player_stats:
                if result['player_id'] == stat['player_id']:
                    result['stats'] = stat  # Add stats to the draft result

        return jsonify(draft_results)
    else:
        return jsonify({"error": "No draft results available for this league."}), 404

@app.route('/api/teams/<league_id>')
def get_teams(league_id):
    lg = league.League(oauth, league_id)
    teams = lg.teams()

    # Create a dictionary to hold team details along with their players
    team_data = {}

    for team_key in teams.keys():
        team = teams[team_key]
        # Fetch the roster for each team
        roster = lg.roster(team['team_id'])  # Use team_id to get the roster
        team_data[team['name']] = {
            'team_key': team_key,
            'players': roster
        }

    return jsonify(team_data)

@app.route('/api/endpoints')
def get_endpoints():
    endpoints = {
        "Leagues": "/fantasy/v2/leagues;league_keys={league_key}",
        "Teams": "/fantasy/v2/teams;team_keys={team_key}",
        "Players": "/fantasy/v2/players;player_keys={player_key}",
        "Matchups": "/fantasy/v2/matchups;league_keys={league_key}",
        "Standings": "/fantasy/v2/standings;league_keys={league_key}",
        "Drafts": "/fantasy/v2/drafts;league_keys={league_key}",
        "Scoring": "/fantasy/v2/scoring;league_keys={league_key}",
        "Transactions": "/fantasy/v2/transactions;league_keys={league_key}",
        "Settings": "/fantasy/v2/settings;league_keys={league_key}",
    }
    return jsonify(endpoints)

if __name__ == '__main__':
    app.run(debug=True)