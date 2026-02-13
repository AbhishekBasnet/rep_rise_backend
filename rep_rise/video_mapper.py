import pandas as pd
from django.conf import settings
from pathlib import Path

# Config: Where your links file lives
# Expects a CSV with columns: 'Workout', 'video_url'
LINKS_CSV_PATH = Path('rep_rise/data/Workout_Links.csv')


def load_video_map():
    """
    Reads the CSV once and returns a dictionary: {'Bench Press': 'http...', ...}
    """
    csv_path = settings.BASE_DIR / LINKS_CSV_PATH

    video_map = {}

    if csv_path.exists():
        try:
            # Read CSV
            df = pd.read_csv(csv_path)

            # Clean column names
            df.columns = df.columns.str.strip()

            # Ensure we have the right columns (flexible check)
            # Adjust these names to match your actual CSV headers
            key_col = 'Workout'
            val_col = 'video_url'

            # Simple normalization to ensure matches (strip whitespace)
            if key_col in df.columns and val_col in df.columns:
                for _, row in df.iterrows():
                    # Map: "Push Up" -> "youtube.com/..."
                    name = str(row[key_col]).strip()
                    url = str(row[val_col]).strip()
                    if url and url.lower() != 'nan':
                        video_map[name] = url

        except Exception as e:
            print(f"Error loading video map: {e}")

    return video_map


def inject_urls(workout_plan_json):
    """
    Takes the pure AI JSON response and injects video URLs.
    """
    # 1. Load the map
    url_map = load_video_map()

    if not url_map:
        return workout_plan_json  # Return original if map fails

    # 2. Iterate and Patch
    # The structure is {'Day 1': [ {exercise data}, ... ], ...}
    enriched_plan = {}

    for day, exercises in workout_plan_json.items():
        day_list = []
        for ex in exercises:
            # Copy the exercise dict to be safe
            new_ex = ex.copy()

            # Lookup the URL using the exercise name
            # We try exact match first
            ex_name = ex.get('exercise', '').strip()
            new_ex['video_url'] = url_map.get(ex_name, "")

            day_list.append(new_ex)

        enriched_plan[day] = day_list

    return enriched_plan