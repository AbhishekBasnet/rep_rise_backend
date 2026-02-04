import os
import pandas as pd
import random
from django.conf import settings

# Path to your dataset.
# Make sure to create a 'data' folder inside your app and put Workout.csv there.
CSV_PATH = os.path.join(settings.BASE_DIR, 'rep_rise/data/Workout.csv')


def generate_workout_plan(weight, height, goal, level):
    """
    Generates a weekly workout plan based on user profile.
    Replicates the logic of filtering the dataset and assigning splits.
    """
    print(f"DEBUG: Looking for file at: {CSV_PATH}")
    try:
        if not os.path.exists(CSV_PATH):
            return {"error": f"Dataset not found at {CSV_PATH}"}

        df = pd.read_csv(CSV_PATH)
        df.columns = df.columns.str.strip()  # Clean whitespace from headers

        # --- LOGIC: Define Split based on Fitness Level ---
        if level == 'beginner':
            # 3 Days Full Body
            days = ['Monday', 'Wednesday', 'Friday']
            split_type = 'Full Body'
            exercises_per_day = 4
        elif level == 'intermediate':
            # 4 Days Upper/Lower
            days = ['Monday', 'Tuesday', 'Thursday', 'Friday']
            split_type = 'Upper/Lower'
            exercises_per_day = 5
        else:  # expert
            # 5 Days Body Part Split (Bro Split)
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            split_type = 'Body Part Split'
            exercises_per_day = 6

        plan = {
            "summary": {
                "level": level,
                "goal": goal,
                "split": split_type
            },
            "schedule": {}
        }

        # --- LOGIC: Select Exercises ---
        # This is a heuristic adaptation of your notebook logic
        for i, day in enumerate(days):
            daily_workout = []

            if level == 'expert':
                # Assign specific body parts to days for experts
                body_parts = ['Chest', 'Back', 'Legs', 'Arms', 'Shoulders']
                target = body_parts[i % len(body_parts)]
                filtered_df = df[df['Body Part'].str.contains(target, case=False, na=False)]
            elif level == 'intermediate':
                # Upper vs Lower
                if i % 2 == 0:  # Mon/Thu = Upper
                    filtered_df = df[df['Body Part'].isin(['Chest', 'Back', 'Arms', 'Shoulders'])]
                else:  # Tue/Fri = Lower
                    filtered_df = df[df['Body Part'].isin(['Legs'])]
            else:
                # Beginner: Mix of everything
                filtered_df = df

            # Randomly sample exercises to create variety
            # In a real ML model, you would use weights/scores here
            if not filtered_df.empty:
                # Get random sample, handle case if df is smaller than required count
                count = min(len(filtered_df), exercises_per_day)
                selected = filtered_df.sample(n=count)
                daily_workout = selected[['Workout', 'Sets', 'Reps per Set']].to_dict(orient='records')

            plan["schedule"][day] = daily_workout

        return plan

    except Exception as e:
        return {"error": f"Calculation failed: {str(e)}"}