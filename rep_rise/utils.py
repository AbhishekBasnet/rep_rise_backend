import pandas as pd
from django.conf import settings
from pathlib import Path

# Make sure this path matches exactly where your CSV is saved
LINKS_CSV_PATH = Path('rep_rise/data/Workout_Links.csv')

# Global cache so we don't read the CSV from disk on every API call
_EXERCISE_VIDEO_MAP = None


def _load_video_map():
    global _EXERCISE_VIDEO_MAP

    if _EXERCISE_VIDEO_MAP is not None:
        return _EXERCISE_VIDEO_MAP

    csv_path = settings.BASE_DIR / LINKS_CSV_PATH
    _EXERCISE_VIDEO_MAP = {}

    if csv_path.exists():
        df = pd.read_csv(csv_path)

        # Clean column names to match your screenshot exactly
        df.columns = df.columns.str.strip()

        # We map the 'Workout' column to the 'Links' column
        if 'Workout' in df.columns and 'Links' in df.columns:
            for _, row in df.iterrows():
                workout_name = str(row['Workout']).strip().lower()
                link = str(row['Links']).strip()

                # Filter out empty rows
                if workout_name and workout_name != 'nan' and link and link != 'nan':
                    _EXERCISE_VIDEO_MAP[workout_name] = link
    else:
        print(f"Warning: Links dataset not found at {csv_path}")

    return _EXERCISE_VIDEO_MAP


def get_video_link(exercise_name):
    """
    Takes an exercise name from ml_logic, finds it in the CSV, and returns the URL.
    """
    if not exercise_name:
        return None

    video_map = _load_video_map()

    # Lowercase everything to ensure 'Chest flyes' matches 'chest flyes'
    key = exercise_name.strip().lower()
    return video_map.get(key, None)