import json
import logging
from pathlib import Path
import sys
import csv
import time
import tidalapi
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Session file path
oauth_file = Path("tidal-session-A.json")


def datetime_to_iso(dt_obj):
    """Convert datetime object to ISO format string"""
    return dt_obj.isoformat() if isinstance(dt_obj, datetime) else str(dt_obj)


def save_session_manually(session, file_path):
    """Manually save session (compatible with older tidalapi versions)"""
    try:
        session_data = {
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'token_type': 'Bearer',
            'expiry_time': datetime_to_iso(session.expiry_time)
        }
        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2)
        logger.info(f"Session saved to: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save session: {str(e)}")
        return False


def login_tidal_session():
    """Log in to TIDAL account"""
    session = tidalapi.Session()

    # Try loading existing session from file
    if oauth_file.exists():
        logger.info("Session file detected, attempting to load...")
        try:
            with open(oauth_file, 'r') as f:
                session_data = json.load(f)
            if session.load_oauth_session(
                    session_data['token_type'],
                    session_data['access_token'],
                    session_data['refresh_token'],
                    session_data['expiry_time']
            ):
                logger.info("Session loaded successfully!")
                return session
        except Exception as e:
            logger.warning(f"Failed to load session: {str(e)}")

    # Perform OAuth login if needed
    logger.info("Please authorize TIDAL account access (browser will open)...")
    try:
        login, future = session.login_oauth()
        logger.info(f"Visit: {login.verification_uri_complete}")
        logger.info(f"Or enter code: {login.user_code} at {login.verification_uri}")
        future.result()  # Wait for login completion

        if session.check_login():
            logger.info("OAuth login successful!")
            save_session_manually(session, oauth_file)
            return session
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")

    return None


def export_favorites_to_csv(session):
    """Export favorites to CSV files"""
    logger.info("Starting favorites export...")

    # 1. Export favorite tracks
    with open('fav_tracks.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['id', 'date_added', 'artist', 'album', 'title'])
        track_count = 0
        for track in session.user.favorites.tracks():
            writer.writerow([
                track.id,
                track.user_date_added.isoformat(),
                track.artist.name,
                track.album.name,
                track.name
            ])
            track_count += 1
        logger.info(f"Exported {track_count} tracks to fav_tracks.csv")

    # 2. Export favorite albums
    with open('fav_albums.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['id', 'date_added', 'artist', 'title'])
        album_count = 0
        for album in session.user.favorites.albums():
            writer.writerow([
                album.id,
                album.user_date_added.isoformat(),
                album.artist.name,
                album.name
            ])
            album_count += 1
        logger.info(f"Exported {album_count} albums to fav_albums.csv")

    # 3. Export favorite artists
    with open('fav_artists.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['id', 'date_added', 'name'])
        artist_count = 0
        for artist in session.user.favorites.artists():
            writer.writerow([
                artist.id,
                artist.user_date_added.isoformat(),
                artist.name
            ])
            artist_count += 1
        logger.info(f"Exported {artist_count} artists to fav_artists.csv")

    # 4. Export playlists (created and favorited)
    with open('fav_playlists.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['id', 'created', 'type', 'name', 'creator'])
        playlist_count = 0
        for playlist in session.user.playlist_and_favorite_playlists():
            # Determine playlist type (owned or favorited)
            pl_type = "OWNED" if playlist.creator.id == session.user.id else "FAVORITE"
            writer.writerow([
                playlist.id,
                playlist.created.isoformat(),
                pl_type,
                playlist.name,
                playlist.creator.name
            ])
            playlist_count += 1
        logger.info(f"Exported {playlist_count} playlists to fav_playlists.csv")


if __name__ == "__main__":
    logger.info("===== TIDAL Favorites Exporter =====")
    session = login_tidal_session()

    if session:
        logger.info(f"Successfully logged in as user: {session.user.id}")
        export_favorites_to_csv(session)
        logger.info("Export complete! Check CSV files in current directory")
    else:
        logger.error("Login failed, exiting program")
        sys.exit(1)
