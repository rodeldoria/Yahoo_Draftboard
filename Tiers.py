import logging
import pandas as pd
import pdfplumber
import os
import re

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

def setup_logging():
    """Set up logging for the application."""
    logging.basicConfig(level=logging.DEBUG)

def create_upload_directory():
    """Create the uploads directory if it doesn't exist."""
    os.makedirs('./uploads', exist_ok=True)

# Main function to demonstrate usage
def main():
    setup_logging()
    create_upload_directory()
    
    # Example usage:
    # file_path = './uploads/example.csv'  # or './uploads/example.pdf'
    # player_data = process_uploaded_file(file_path)
    # print(player_data)
    
    # logo_url = get_team_logo_url('SEA')
    # print(f"Team logo URL: {logo_url}")

if __name__ == '__main__':
    main()