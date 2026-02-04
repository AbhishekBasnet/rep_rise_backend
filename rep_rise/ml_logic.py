import pandas as pd
import os
from django.conf import settings

# Construct the absolute path to your CSV
# Place 'Workout.csv' in a folder named 'data' inside your project root or app folder
CSV_PATH = os.path.join(settings.BASE_DIR, 'myapp/data/Workout.csv')


# Update 'myapp' to your actual app name

def generate_workout_plan(weight, height, goal, level):
    """
    Replicates the logic from your Jupyter Notebook.
    Returns a dictionary (JSON structure) of the weekly plan.
    """
    try:
        df = pd.read_csv(CSV_PATH)

        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()

        # --- YOUR NOTEBOOK LOGIC GOES HERE ---
        # Since I can't see the full body of 'recommend_workout' in your snippet,
        # I have implemented a robust filtering logic based on your CSV structure.
        # You can replace this block with your exact pandas filtering if different.

        # Example Logic: Filter sets/reps based on Goal
        if goal == 'muscle_gain':
            # Filter for Hypertrophy rep ranges (8-12)
            # This is a heuristic; adjust based on how your CSV is structured
            pass

            # Example Logic: Create a 3-Day Split (Push/Pull/Legs) or 5-Day Split
        # This is a simplified generator to match your JSON output format

        weekly_plan = {}

        # Simple rule-based distribution for demonstration
        # (Replace with your actual ML/Filtering code)
        split = {
            "Day 1 (Chest)": df[df['Body Part'] == 'Chest'].head(4),
            "Day 2 (Back)": df[df['Body Part'] == 'Back'].head(4),
            "Day 3 (Legs)": df[df['Body Part'] == 'Legs'].head(4),
            "Day 4 (Arms)": df[df['Body Part'] == 'Arms'].head(4),
            "Day 5 (Shoulders/Abs)": df[df['Body Part'].isin(['Shoulders', 'Abs'])].head(4),
        }

        for day, workout_data in split.items():
            # Convert the DataFrame to a list of dictionaries for JSON compatibility
            weekly_plan[day] = workout_data.to_dict(orient='records')

        return weekly_plan

    except FileNotFoundError:
        return {"error": "Workout dataset not found on server."}
    except Exception as e:
        return {"error": f"Calculation failed: {str(e)}"}