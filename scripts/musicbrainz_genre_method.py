import pandas as pd
import musicbrainzngs
import time
import os

# Setup MusicBrainz
musicbrainzngs.set_useragent("spotify-genre-analyzer", "1.0", "jbrinson@uoregon.edu")

# Load your data
df = pd.read_csv('data/raw/Spotify_Streaming_History_Combined.csv')
print(f"Total tracks: {len(df):,}")

# Caches
artist_cache = {}
genres = []

# Check for existing progress
progress_file = 'data/processed/musicbrainz_genre_progress.csv'
start_index = 0

if os.path.exists(progress_file):
    existing = pd.read_csv(progress_file)
    genres = existing['genre'].tolist()
    start_index = len(genres)
    print(f"Resuming from track {start_index + 1}")

def get_genre_from_musicbrainz(artist_name):
    """Get genres from MusicBrainz"""
    
    if artist_name.lower() in artist_cache:
        return artist_cache[artist_name.lower()]
    
    try:
        # Search for artist
        result = musicbrainzngs.search_artists(artist=artist_name, limit=5)
        
        if result['artist-list']:
            # Try to find the best match
            for artist in result['artist-list']:
                mb_artist_name = artist.get('name', '').lower()
                our_artist_name = artist_name.lower()
                
                # Basic name matching
                if (mb_artist_name == our_artist_name or 
                    mb_artist_name in our_artist_name or 
                    our_artist_name in mb_artist_name):
                    
                    # Get artist details with tags (genres)
                    artist_id = artist['id']
                    artist_details = musicbrainzngs.get_artist_by_id(artist_id, includes=['tags'])
                    
                    tags = artist_details['artist'].get('tag-list', [])
                    if tags:
                        # Extract genre tags (filter out non-genre tags)
                        genre_tags = [tag['name'] for tag in tags 
                                    if int(tag.get('count', 0)) > 0 and 
                                    tag['name'] not in ['favorites', 'seen live', 'own albums']]
                        
                        if genre_tags:
                            genre_result = ', '.join(genre_tags[:5])  # Limit to top 5 genres
                            artist_cache[artist_name.lower()] = genre_result
                            print(f"🎵 MusicBrainz: {artist_name} → {genre_result}")
                            return genre_result
            
            print(f"❌ No genres in MusicBrainz: {artist_name}")
            artist_cache[artist_name.lower()] = 'Unknown'
            return 'Unknown'
        else:
            print(f"❌ Artist not found in MusicBrainz: {artist_name}")
            artist_cache[artist_name.lower()] = 'Unknown'
            return 'Unknown'
            
    except Exception as e:
        print(f"❌ MusicBrainz error for {artist_name}: {e}")
        # Rate limit handling
        if "503" in str(e) or "rate" in str(e).lower():
            print("⚠️ Rate limited, waiting 1 second...")
            time.sleep(1)
        artist_cache[artist_name.lower()] = 'Error'
        return 'Error'

# Process tracks
for i in range(start_index, len(df)):
    try:
        artist_name = df.iloc[i]['master_metadata_album_artist_name']
        
        print(f"Processing {i+1}: {artist_name}")
        
        genre = get_genre_from_musicbrainz(artist_name)
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
    
    # MusicBrainz is more generous with rate limits, but still be polite
    time.sleep(0.1)  # 10 requests/second is usually fine

# Final save
df['genre'] = genres
df.to_csv('data/processed/spotify_data_with_musicbrainz_genres.csv', index=False)

if os.path.exists(progress_file):
    os.remove(progress_file)

print(f"Complete! Processed {len(df):,} tracks")