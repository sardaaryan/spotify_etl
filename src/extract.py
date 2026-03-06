import os
import json
import base64
import requests
from urllib.parse import urlencode, parse_qs, urlparse
from dotenv import load_dotenv, set_key
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Load environment variables globally for the static keys
load_dotenv()

# Fail-Fast Env Validation
REQUIRED_ENV_VARS = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI"]
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}. Check your .env file.")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
ENV_FILE_PATH = ".env"

def get_first_time_tokens() -> str:
    """1-time manual flow to get the initial Refresh Token and save it to .env"""
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-read-recently-played", 
    }
    
    print(f"\n[ACTION REQUIRED] Please click this link to authorize your App:\n{auth_url}?{urlencode(params)}\n")
    print("After agreeing, you will be redirected to an error page (this is normal!).")
    redirected_url = input("Copy the ENTIRE URL from your browser address bar and paste it here: ")

    parsed_url = urlparse(redirected_url)
    code = parse_qs(parsed_url.query).get('code', [None])[0]

    if not code:
        raise ValueError("Could not find 'code' in the URL. Did you paste the whole thing?")

    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(token_url, headers=headers, data=data, timeout=10)
    response.raise_for_status()
    tokens = response.json()

    # Write the new token to the disk
    set_key(ENV_FILE_PATH, "SPOTIFY_REFRESH_TOKEN", tokens["refresh_token"])
    print("Success! Refresh Token safely locked in your .env file.")
    
    return tokens["access_token"]

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=4), 
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def get_access_token() -> str:
    """Automated flow to get a fresh Access Token using the Refresh Token."""
    load_dotenv(override=True)
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    if not refresh_token:
        return get_first_time_tokens()

    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = requests.post(token_url, headers=headers, data=data, timeout=10)
    response.raise_for_status()
    return response.json()["access_token"]

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def fetch_recently_played(access_token: str, after_timestamp: int = None):
    """Fetch the last 50 played tracks, handling API rate limits natively."""
    url = "https://api.spotify.com/v1/me/player/recently-played"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Max out the limit to 50
    params = {"limit": 50}

    # If we pass a timestamp, add the 'after' parameter to strictly pull new data
    if after_timestamp:
        params["after"] = after_timestamp

    response = requests.get(url, headers=headers, params=params,timeout=10)
    response.raise_for_status() 
    return response.json()

# Create an empty dictionary at the top level to store artist genres in memory
ARTIST_CACHE = {}

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def fetch_artist_details(access_token: str, artist_id: str):
    """Fetches genres for a specific artist, utilizing an in-memory cache."""
    # 1. THE CACHE CHECK: If we already looked up this artist, return it instantly!
    if artist_id in ARTIST_CACHE:
        print(f"   [Cache Hit] Using stored genres for artist {artist_id}")
        return ARTIST_CACHE[artist_id]

    url = f"https://api.spotify.com/v1/artists/{artist_id}" 
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    genres = data.get('genres', [])
    
    # 2. SAVE TO CACHE: Remember these genres for the next time this artist appears
    ARTIST_CACHE[artist_id] = genres
    return genres

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def fetch_track_metadata(access_token: str, track_id: str):
    """Fetches detailed metadata for a single track and merges artist genres."""
    url = f"https://api.spotify.com/v1/tracks/{track_id}" 
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 404:
        return None
        
    response.raise_for_status()
    data = response.json()
    
    # FIX 1: Get the popularity score directly from the TRACK response
    track_popularity = data.get('popularity', 0)
    
    artist_id = data['artists'][0]['id']
    
    # FIX 2: This will now use our smart caching function
    genres = fetch_artist_details(access_token, artist_id)
    
    return {
        "track_id": track_id,
        "track_name": data['name'],
        "artist_name": data['artists'][0]['name'],
        "artist_id": artist_id,
        "album_name": data['album']['name'],
        "artist_genres": genres,
        "popularity": track_popularity  # Now correctly mapped to the track!
    }


if __name__ == "__main__":
    print("Starting Spotify Extraction Engine...")
    
    # Create the data folder if it doesn't exist
    os.makedirs("data", exist_ok=True)

    token = get_access_token()

    # Fetch recent tracks
    data = fetch_recently_played(token)

    # Dump the raw output to a local file for inspection
    with open("data/raw_response.json", "w") as f:
        json.dump(data, f, indent=4)
        
    items = data.get("items", [])
    print(f"\nSuccessfully fetched {len(items)} tracks!")
    
    if items:
        print("\n--- Testing Dimensional Data Extraction ---")
        first_track = items[0]['track']
        track_id = first_track['id']
        
        print(f"Fetching deep metadata for: {first_track['name']} (ID: {track_id})")
        
        # Test our new function!
        metadata = fetch_track_metadata(token, track_id)
        
        print("\nMetadata Successfully Extracted (Preview for dim_tracks):")
        print(json.dumps(metadata, indent=4))