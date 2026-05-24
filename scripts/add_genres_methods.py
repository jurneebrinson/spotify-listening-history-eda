import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize credentials
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, 
    client_secret=client_secret,
    cache_handler=None
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Load your data
df = pd.read_csv('data/raw/Spotify_Streaming_History_Combined.csv')
print(f"Total tracks: {len(df):,}")

# Artist cache - this is the key improvement!
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

def get_genre_from_artist(artist_name):
    """Get genre directly from artist search - FIXED VERSION"""
    
    # Check cache first
    if artist_name.lower() in artist_cache:
        return artist_cache[artist_name.lower()]
    
    try:
        # Search for artist directly
        results = sp.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
        
        if results['artists']['items']:
            artist = results['artists']['items'][0]
            
            # Verify it's the right artist (fuzzy matching)
            spotify_artist_name = artist['name'].lower()
            our_artist_name = artist_name.lower()
            
            # Basic name matching
            name_match = (spotify_artist_name in our_artist_name or 
                         our_artist_name in spotify_artist_name or
                         artist_name.split()[0].lower() == spotify_artist_name.split()[0].lower())
            
            if name_match:
                # FIX: Check if genres array has content, not just if it exists
                if artist.get('genres') and len(artist['genres']) > 0:
                    genre_result = ', '.join(artist['genres'])
                    artist_cache[artist_name.lower()] = genre_result
                    print(f"✅ Found: {artist_name} → {genre_result}")
                    return genre_result
                else:
                    # Artist found but no genres in Spotify's database
                    print(f"🎵 Artist found but no genres: {artist_name}")
                    artist_cache[artist_name.lower()] = 'Unknown'
                    return 'Unknown'
            else:
                print(f"🔍 Name mismatch: '{artist_name}' vs '{artist['name']}'")
                # Try a more relaxed search
                return relaxed_artist_search(artist_name)
        else:
            print(f"❌ Artist not found: {artist_name}")
            artist_cache[artist_name.lower()] = 'Unknown'
            return 'Unknown'
            
    except Exception as e:
        print(f"❌ Error searching for {artist_name}: {e}")
        artist_cache[artist_name.lower()] = 'Error'
        return 'Error'

def relaxed_artist_search(artist_name):
    """Try a more relaxed search if exact match fails"""
    try:
        results = sp.search(q=artist_name, type='artist', limit=3)
        
        for artist in results['artists']['items']:
            spotify_name = artist['name'].lower()
            our_name = artist_name.lower()
            
            # More relaxed matching
            if (spotify_name == our_name or 
                spotify_name in our_name or 
                our_name in spotify_name or
                artist_name.split()[0].lower() == spotify_name.split()[0].lower()):
                
                if artist.get('genres') and len(artist['genres']) > 0:
                    genre_result = ', '.join(artist['genres'])
                    artist_cache[artist_name.lower()] = genre_result
                    print(f"✅ Found via relaxed: {artist_name} → {genre_result}")
                    return genre_result
        
        print(f"❌ No match even with relaxed search: {artist_name}")
        artist_cache[artist_name.lower()] = 'Unknown'
        return 'Unknown'
        
    except Exception as e:
        print(f"❌ Relaxed search error for {artist_name}: {e}")
        return 'Unknown'

# Process tracks
for i in range(start_index, len(df)):
    try:
        # Get artist name from your CSV
        artist_name = df.iloc[i]['master_metadata_album_artist_name']
        
        print(f"Processing {i+1}: {artist_name}")
        
        # Get genre directly from artist
        genre = get_genre_from_artist(artist_name)
        genres.append(genre)
        
    except Exception as e:
        print(f"Error on row {i}: {e}")
        genres.append('Error')
    
    # Progress updates
    if (i + 1) % 100 == 0:
        percent = (i + 1) / len(df) * 100
        unique_artists = len(artist_cache)
        unknown_count = genres.count('Unknown')
        success_count = len(genres) - unknown_count - genres.count('Error')
        success_rate = (success_count / (i + 1)) * 100
        
        print(f"Progress: {i + 1:,}/{len(df):,} ({percent:.1f}%)")
        print(f"Success rate: {success_rate:.1f}% | Unique artists: {unique_artists}")
    
    # Save progress every 500 tracks
    if (i + 1) % 500 == 0:
        temp_df = df.iloc[:i+1].copy()
        temp_df['genre'] = genres
        temp_df.to_csv(progress_file, index=False)
        print(f"💾 Progress saved at track {i + 1}")
    
    # Rate limiting
    time.sleep(0.3)

# Final save
df['genre'] = genres
df.to_csv('data/processed/spotify_data_with_genres.csv', index=False)

if os.path.exists(progress_file):
    os.remove(progress_file)

# Final stats
unknown_count = genres.count('Unknown')
error_count = genres.count('Error')
success_count = len(genres) - unknown_count - error_count
success_rate = (success_count / len(genres)) * 100

print(f"\n🎉 Complete! Processed {len(df):,} tracks")
print(f"📊 Success rate: {success_rate:.1f}%")
print(f"🎵 Unique artists found: {len(artist_cache):,}")
print(f"❓ Unknown genres: {unknown_count:,}")
print(f"❌ Errors: {error_count:,}")