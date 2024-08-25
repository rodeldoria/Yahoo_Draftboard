from yahoo_oauth import OAuth2
import json  # Import json module
import xml.etree.ElementTree as ET  # Import XML parser
from yahoo_fantasy_api import League  # Import the League class

# Initialize OAuth2 using the credentials from the JSON file
oauth = OAuth2(None, None, from_file='oauth2.json')

# Check if the token is valid, refresh if necessary
if not oauth.token_is_valid():
    oauth.refresh_access_token()

# Use the specified league ID
league_id = 818153  # Your league ID
league_key = f"nfl.l.{league_id}"  # Construct the league key for NFL

# Initialize the Yahoo Fantasy API client with the league_id
league_api = League(oauth, league_id)  # Use the League class with league_id

# Example: Get league details
try:
    response = oauth.session.get(f"https://fantasysports.yahooapis.com/fantasy/v2/leagues;league_keys={league_key}")

    # Check the response status code
    response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)

    # Parse the XML response
    root = ET.fromstring(response.text)
    
    # Print the entire XML response for debugging
    print("XML Response:", response.text)

    # Define the namespaces
    namespaces = {
        'yahoo': 'http://www.yahooapis.com/v1/base.rng',
        '': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'  # Default namespace
    }

    # Extract league details from the XML
    league_elem = root.find('.//{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league', namespaces)

    # Check if the league element was found
    if league_elem is not None:
        league_details = {
            "league_key": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league_key').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league_key') is not None else "N/A",
            "league_id": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league_id').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league_id') is not None else "N/A",
            "name": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}name').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}name') is not None else "N/A",
            "url": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}url').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}url') is not None else "N/A",
            "draft_status": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}draft_status').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}draft_status') is not None else "N/A",
            "num_teams": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}num_teams').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}num_teams') is not None else "N/A",
            "scoring_type": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}scoring_type').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}scoring_type') is not None else "N/A",
            "league_type": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league_type').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}league_type') is not None else "N/A",
            "season": league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}season').text if league_elem.find('{http://fantasysports.yahooapis.com/fantasy/v2/base.rng}season') is not None else "N/A",
        }
        print("League Details:", league_details)  # Print league details
    else:
        print("Error: League element not found in the response.")

except ET.ParseError:
    print("Error: Response content is not valid XML.")
    print(f"Response text: {response.text}")  # Print the raw response text
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")  # Handle HTTP errors
except Exception as err:
    print(f"An error occurred: {err}")  # Handle other exceptions