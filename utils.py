import pandas as pd
import pdfplumber
import re

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
                            })
    
    except Exception as e:
        print(f"Error processing PDF: {e}")  # Debuggin
