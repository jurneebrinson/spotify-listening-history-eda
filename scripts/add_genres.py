import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import os
from dotenv import load_dotenv

load_dotenv()

os.makedirs("data/processed", exist_ok=True)

# Initialize credentials
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, 
    client_secret=client_secret,
    cache_handler=None  # This disables caching
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Load your data
df = pd.read_csv('data/raw/Spotify_Streaming_History_Combined.csv')
print(f"Total tracks: {len(df):,}")

# Use artist caching to minimize API calls
artist_cache = {}
genres = []

# Check for existing progress
progress_file = 'data/processed/genre_progress.csv'
start_index = 0

if os.path.exists(progress_file):
    existing = pd.read_csv(progress_file)
    genres = existing['genre'].tolist()
    start_index = len(genres)
    print(f"Resuming from track {start_index + 1}")

def get_genre_by_search(track_name, artist_name):
    """Fallback method: search by track and artist name"""
    try:
        # Search for the track
        query = f"track:{track_name} artist:{artist_name}"
        results = sp.search(q=query, type='track', limit=1)
        
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            artist_id = track['artists'][0]['id']
            
            # Get artist info for genres
            artist = sp.artist(artist_id)
            if artist['genres']:
                return ', '.join(artist['genres'])
        
        return None
    except Exception as e:
        print(f"Search fallback error for {track_name} by {artist_name}: {e}")
        return None

def get_genre_with_fallback(track_uri, track_name, artist_name, row_index):
    """Try multiple methods to get genre"""
    
    # Method 1: Try with track URI first
    try:
        track = sp.track(track_uri)
        artist_id = track['artists'][0]['id']
        
        # Check cache first
        if artist_id in artist_cache:
            return artist_cache[artist_id]
        
        # New artist - fetch genres
        artist = sp.artist(artist_id)
        if artist['genres']:
            genre = ', '.join(artist['genres'])
            artist_cache[artist_id] = genre
            return genre
        else:
            # No genres from URI method, try search fallback
            print(f"🎵 No genres via URI for row {row_index}, trying search...")
            genre = get_genre_by_search(track_name, artist_name)
            if genre:
                artist_cache[artist_id] = genre  # Cache the found genre
                return genre
            return 'Unknown'
            
    except Exception as e:
        print(f"URI method failed for row {row_index}, trying search fallback...")
        # Method 2: Try search fallback if URI method fails
        genre = get_genre_by_search(track_name, artist_name)
        if genre:
            return genre
        return 'Unknown'

# Process tracks
for i in range(start_index, len(df)):
    try:
        # Get track data
        track_uri = df.iloc[i]['spotify_track_uri']
        track_name = df.iloc[i]['master_metadata_track_name']  # Adjust column name if needed
        artist_name = df.iloc[i]['master_metadata_album_artist_name']  # Adjust column name if needed
        
        print(f"Processing track {i+1}: {track_name} by {artist_name}")
        
        # Get genre with fallback logic
        genre = get_genre_with_fallback(track_uri, track_name, artist_name, i+1)
        genres.append(genre)
        
    except Exception as e:
        print(f"Error on row {i}: {e}")
        genres.append('Error')
    
    # Progress updates
    if (i + 1) % 100 == 0:
        percent = (i + 1) / len(df) * 100
        unique_artists = len(artist_cache)
        unknown_count = genres.count('Unknown')
        success_rate = ((i + 1 - unknown_count) / (i + 1)) * 100
        print(f"Progress: {i + 1:,}/{len(df):,} ({percent:.1f}%)")
        print(f"  Unique artists: {unique_artists}, Success rate: {success_rate:.1f}%")
    
    # Save progress every 100 tracks (more frequent due to additional API calls)
    if (i + 1) % 100 == 0:
        temp_df = df.iloc[:i+1].copy()
        temp_df['genre'] = genres
        temp_df.to_csv(progress_file, index=False)
        print(f"💾 Progress saved at track {i + 1}")
    
    # Rate limiting - be conservative with additional API calls
    time.sleep(0.6)  # Slightly increased delay

# Final save
df['genre'] = genres
df.to_csv("data/processed/spotify_data_with_genres.csv", index=False)

if os.path.exists(progress_file):
    os.remove(progress_file)

# Summary statistics
unknown_count = genres.count('Unknown')
error_count = genres.count('Error')
success_count = len(genres) - unknown_count - error_count
success_rate = (success_count / len(genres)) * 100

print(f"\n🎉 Complete! Processed {len(df):,} tracks from {len(artist_cache):,} unique artists")
print(f"📊 Success rate: {success_rate:.1f}% ({success_count:,} tracks with genres)")
print(f"❓ Unknown: {unknown_count:,} tracks")
print(f"❌ Errors: {error_count:,} tracks")