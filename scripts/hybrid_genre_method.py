import pandas as pd
import musicbrainzngs
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Setup MusicBrainz
musicbrainzngs.set_useragent("spotify-genre-analyzer", "1.0", "your-email@example.com")

# Setup Spotify
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

# Caches
artist_cache = {}
genres = []
methods = []

# Manual genre corrections for obviously wrong classifications
manual_corrections = {
    'young thug': 'hip hop, trap, rap',
    'ryo fukui': 'jazz, piano jazz',
    '鈴木弘': 'jazz, piano jazz',  # Hiroshi Suzuki
    'bernie worrell': 'funk, p-funk, rock',
    'kaytranada': 'electronic, dance',
    'faye webster': 'alternative, indie',
    'kali uchis': 'latino, r&b, pop',
    'goldlink': 'hip hop, electronic',
    'n.e.r.d': 'hip hop, rock',
    'smino': 'r&b, soul, electronic, hip hop',
    'zack fox': 'hip hop',
    'premo rice': 'hip hop',
    'comethazine': 'hip hop',
    'young nudy': 'hip hop',
    'lil yachty': 'hip hop',
    'nle choppa': 'hip hop',
    'maxo kream': 'hip hop',
    'tisakorean': 'hip hop',
    'monte booker': 'dance, electronic',
    'frank ocean': 'alternative, r&b',
    'sam gellaitry': 'electronic',
    'carpenters': 'pop, soft rock',
    'aminé': 'hip hop',
    'mk.gee': 'alternative, indie',
    'moneybagg yo': 'hip hop',
    'glorilla': 'hip hop',
    'megan thee stallion': 'hip hop',
    'don toliver': 'hip hop',
    'larry june': 'hip hop'

    # Add more corrections as you find them
}

# Check for existing progress
progress_file = 'data/processed/hybrid_genre_progress.csv'
start_index = 0

if os.path.exists(progress_file):
    existing = pd.read_csv(progress_file)
    genres = existing['genre'].tolist()
    if 'method' in existing.columns:
        methods = existing['method'].tolist()
    else:
        methods = ['unknown'] * len(genres)
    
    start_index = len(genres)
    print(f"Resuming from track {start_index + 1}")
    print(f"Loaded {len(genres)} genres and {len(methods)} methods")

def get_genre_from_spotify(artist_name):
    """Get genres from Spotify (PRIMARY SOURCE)"""
    try:
        results = sp.search(q=artist_name, type='artist', limit=3)
        
        if results['artists']['items']:
            # Try to find the best match among top 3 results
            for artist in results['artists']['items']:
                spotify_name = artist['name'].lower()
                our_name = artist_name.lower()
                
                # Better name matching
                if (spotify_name == our_name or 
                    our_name in spotify_name or 
                    spotify_name in our_name or
                    artist_name.split()[0].lower() == spotify_name.split()[0].lower()):
                
                    if artist.get('genres') and len(artist['genres']) > 0:
                        genre_result = ', '.join(artist['genres'])
                        print(f"🎵 Spotify: {artist_name} → {genre_result}")
                        return genre_result, "spotify"
        
        return None, "spotify_no_genres"
            
    except Exception as e:
        print(f"❌ Spotify error for {artist_name}: {e}")
        return None, "spotify_error"

def get_genre_from_musicbrainz(artist_name):
    """Get genres from MusicBrainz (FALLBACK ONLY)"""
    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=3)
        
        if result['artist-list']:
            for artist in result['artist-list']:
                mb_artist_name = artist.get('name', '').lower()
                our_artist_name = artist_name.lower()
                
                # Strict name matching for MusicBrainz
                if (mb_artist_name == our_artist_name or 
                    our_artist_name in mb_artist_name):
                    
                    try:
                        artist_id = artist['id']
                        artist_details = musicbrainzngs.get_artist_by_id(artist_id, includes=['tags'])
                        
                        tags = artist_details['artist'].get('tag-list', [])
                        if tags:
                            # Only use tags with significant votes and filter out bad tags
                            genre_tags = []
                            for tag in tags:
                                tag_name = tag['name'].lower()
                                count = int(tag.get('count', 0))
                                
                                # Filter conditions
                                if (count > 2 and  # Minimum votes
                                    tag_name not in ['favorites', 'seen live', 'own albums', 'awesome'] and
                                    len(tag_name) > 2 and
                                    # Filter out obviously wrong tags for music genres
                                    tag_name not in ['canadian', 'american', 'british', 'japanese', 'english'] and
                                    not any(bad in tag_name for bad in ['anime', 'meme', 'comedy', 'parody'])):
                                    
                                    genre_tags.append(tag['name'])
                            
                            if genre_tags:
                                genre_result = ', '.join(genre_tags[:3])
                                print(f"🎵 MusicBrainz (fallback): {artist_name} → {genre_result}")
                                return genre_result, "musicbrainz_fallback"
                    except Exception as e:
                        continue
            
            return None, "musicbrainz_no_reliable_genres"
        else:
            return None, "musicbrainz_not_found"
            
    except Exception as e:
        print(f"❌ MusicBrainz error for {artist_name}: {e}")
        return None, "musicbrainz_error"

def get_genre_hybrid(artist_name):
    """REVISED: Spotify first, then filtered MusicBrainz fallback"""
    
    # Check manual corrections first
    if artist_name.lower() in manual_corrections:
        genre = manual_corrections[artist_name.lower()]
        print(f"📚 Manual correction: {artist_name} → {genre}")
        return genre, "manual_correction"
    
    # Check cache
    if artist_name.lower() in artist_cache:
        genre, method = artist_cache[artist_name.lower()]
        print(f"   Cached: {artist_name} → {genre}")
        return genre, f"cached_{method}"
    
    print(f"   Searching: {artist_name}")
    
    # Try Spotify first (more reliable)
    genre, method = get_genre_from_spotify(artist_name)
    if genre:
        artist_cache[artist_name.lower()] = (genre, method)
        return genre, method
    
    # Fall back to filtered MusicBrainz
    genre, method = get_genre_from_musicbrainz(artist_name)
    if genre:
        artist_cache[artist_name.lower()] = (genre, method)
        return genre, method
    
    print(f"   ❌ No reliable genres found: {artist_name}")
    artist_cache[artist_name.lower()] = ('Unknown', 'both_failed')
    return 'Unknown', 'both_failed'

print(f"Starting processing from track {start_index + 1}...")

# Process tracks
for i in range(start_index, len(df)):
    try:
        artist_name = str(df.iloc[i]['master_metadata_album_artist_name'])
        
        print(f"\n[{i+1}/{len(df)}] Processing: {artist_name}")
        
        genre, method = get_genre_hybrid(artist_name)
        genres.append(genre)
        methods.append(method)
        
    except Exception as e:
        print(f"💥 Major error on row {i}: {e}")
        genres.append('Error')
        methods.append('major_error')
    
    # Progress updates
    if (i + 1) % 100 == 0:
        percent = (i + 1) / len(df) * 100
        unique_artists = len(artist_cache)
        
        method_counts = {}
        for m in methods:
            method_counts[m] = method_counts.get(m, 0) + 1
        
        unknown_count = genres.count('Unknown')
        success_count = len(genres) - unknown_count - genres.count('Error')
        success_rate = (success_count / (i + 1)) * 100
        
        print(f"\n📊 Progress: {i + 1:,}/{len(df):,} ({percent:.1f}%)")
        print(f"Success rate: {success_rate:.1f}% | Unique artists: {unique_artists}")
        print(f"Method breakdown: {method_counts}")
    
    # Save progress every 500 tracks
    if (i + 1) % 100 == 0:
        rows_to_save = min(i + 1, len(genres), len(methods))
        temp_df = df.iloc[:rows_to_save].copy()
        temp_df['genre'] = genres[:rows_to_save]
        temp_df['method'] = methods[:rows_to_save]
        temp_df.to_csv(progress_file, index=False)
        print(f"💾 Progress saved at track {rows_to_save}")
    
    # Rate limiting
    time.sleep(0.3)

# Final save
final_rows = min(len(df), len(genres), len(methods))
result_df = df.iloc[:final_rows].copy()
result_df['genre'] = genres[:final_rows]
result_df['genre_method'] = methods[:final_rows]
result_df.to_csv('data/processed/spotify_data_with_hybrid_genres.csv', index=False)

if os.path.exists(progress_file):
    os.remove(progress_file)

print(f"\n🎉 Complete! Processed {final_rows:,} tracks")