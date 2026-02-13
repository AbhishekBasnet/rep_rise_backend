import os
import pandas as pd
from django.conf import settings
from pathlib import Path
from .utils import get_video_link

# --- CONFIGURATION ---
# Assumes structure: project_root/rep_rise/data/Workout.csv
# We use Path for OS-agnostic handling (Windows/Mac/Linux friendly)
CSV_REL_PATH = Path('rep_rise/data/Workout.csv')


def load_data():
    """
    Loads and cleans the workout dataset.
    """
    # Construct absolute path using Django's BASE_DIR
    csv_path = settings.BASE_DIR / CSV_REL_PATH

    if not csv_path.exists():
        # Fallback for local testing if needed, or raise clear error
        raise FileNotFoundError(f"Dataset not found at {csv_path}. check 'rep_rise/data' folder.")

    df = pd.read_csv(csv_path)

    # Clean column names (remove spaces)
    df.columns = df.columns.str.strip()

    # Clean body part data for easier matching (strip and lower)
    df['Body Part'] = df['Body Part'].str.strip().str.lower()

    # Clean Type of Muscle for filtering (Crucial for the Expert split)
    if 'Type of Muscle' in df.columns:
        df['Type of Muscle'] = df['Type of Muscle'].str.strip().str.lower()

    return df


# --- 1. FITNESS CALCULATIONS ---

def calculate_bmi(weight, height_cm):
    if not height_cm: return 0
    height_m = height_cm / 100
    return round(weight / (height_m ** 2), 2)


def get_fitness_level(age, bmi):
    """
    Matches Notebook Cell 32 Logic exactly.
    """
    # Rule 1: Age > 45 or BMI >= 30 -> Beginner
    if age > 45 or bmi >= 30:
        return "beginner"
    # Rule 2: 25 <= BMI < 30 -> Beginner
    elif 25 <= bmi < 30:
        return "beginner"
    # Rule 3: 18.5 <= BMI < 25 -> Intermediate
    elif 18.5 <= bmi < 25:
        return "intermediate"
    # Default (BMI < 18.5) -> Beginner
    else:
        return "beginner"


def get_workout_goal(weight, ideal_weight):
    if weight > ideal_weight:
        return "fat_loss"
    elif weight < ideal_weight:
        return "muscle_gain"
    else:
        return "maintenance"


# --- 2. WORKOUT SPLIT CONFIGURATION ---

def get_workout_split(goal, fitness_level):
    fitness_level = fitness_level.lower()
    goal = goal.lower()

    if fitness_level == "beginner":
        return {
            "Day 1": ["chest", "back"],
            "Day 2": ["legs", "abs"],
            "Day 3": ["shoulders", "arms"]
        }

    elif fitness_level == "intermediate":
        if goal == "muscle_gain":
            return {
                "Day 1": ["chest"],
                "Day 2": ["back"],
                "Day 3": ["legs"],
                "Day 4": ["shoulders"],
                "Day 5": ["arms"]
            }
        else:  # fat_loss / maintenance
            return {
                "Day 1": ["chest", "back"],
                "Day 2": ["legs"],
                "Day 3": ["shoulders", "arms"],
                "Day 4": ["abs"]
            }

    else:  # expert / advanced
        return {
            "Day 1": ["chest", "triceps"],  # Logic handles mapping 'triceps' -> 'arms'
            "Day 2": ["back", "biceps"],  # Logic handles mapping 'biceps' -> 'arms'
            "Day 3": ["legs"],
            "Day 4": ["shoulders"],
            "Day 5": ["abs"]
        }


def get_exercise_count(fitness_level):
    level = fitness_level.lower()
    if level == "beginner":
        return 3
    elif level == "intermediate":
        return 4
    else:
        return 5


def adjust_sets_reps(bmi, goal):
    # Handles both string variations for safety
    if goal in ["fat_loss", "weight_loss"]:
        return "3", "12-20"

    if bmi < 18.5:
        return "4", "8-12"
    elif bmi > 25:
        return "3", "12-15"
    else:
        return "3-4", "10-12"


# --- 3. EXERCISE SELECTION ---

def select_exercises(df, body_part, max_exercises):
    body_part = body_part.lower()

    # Logic Fix: Map specific muscle requests (Triceps/Biceps) to the "Arms" body part
    # but filter by the 'Type of Muscle' column.
    if body_part in ['triceps', 'biceps']:
        filtered = df[
            (df["Body Part"] == "arms") &
            (df["Type of Muscle"].str.contains(body_part))
            ]
    else:
        filtered = df[df["Body Part"] == body_part]

    if filtered.empty:
        return []

    # Random sample matching notebook logic
    count = min(len(filtered), max_exercises)
    return filtered.sample(n=count).to_dict(orient='records')


# --- 4. MAIN ENTRY POINT ---

def generate_workout_plan(age, height, weight, ideal_weight, fitness_level=None):
    try:
        df = load_data()

        # 1. Calculate stats
        bmi = calculate_bmi(weight, height)
        goal = get_workout_goal(weight, ideal_weight)

        # 2. Determine Level (Calculated vs Override)
        calc_level = get_fitness_level(age, bmi)
        final_level = fitness_level if fitness_level else calc_level

        # 3. Get Configuration
        split = get_workout_split(goal, final_level)
        max_exercises = get_exercise_count(final_level)
        sets, reps = adjust_sets_reps(bmi, goal)

        weekly_plan = {}

        for day_name, body_parts in split.items():
            day_plan = []

            for part in body_parts:
                exercises = select_exercises(df, part, max_exercises)

                for ex in exercises:
                    day_plan.append({
                        "exercise": ex.get('Workout'),
                        "target_muscle": ex.get('Type of Muscle'),
                        "body_part": part,  # Return the requested part name (e.g. 'triceps')
                        "sets": sets,
                        "reps": reps,
                        "rest_time": "60s"
                    })

            weekly_plan[day_name] = day_plan

        return {
            "status": "success",
            "meta": {
                "bmi": bmi,
                "fitness_level": final_level,
                "goal": goal,
            },
            "schedule": weekly_plan
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# --- 5. PIPELINE: ENRICHMENT & PROGRESS ---

def attach_video_links(schedule_data):
    """
    Step 2: Iterates through the generated schedule and injects 'video_url'.
    """
    for day, exercises in schedule_data.items():
        if isinstance(exercises, list):
            for ex in exercises:
                # ex is a dict like {'exercise': 'Bench Press', ...}
                ex_name = ex.get('exercise')
                video_url = get_video_link(ex_name)

                # Inject the field (this modifies the dictionary in place)
                ex['video_url'] = video_url

    return schedule_data


def initialize_progress(schedule_data):
    """
    Step 3: Wraps the schedule and adds a progress tracker.

    Old Structure: {'Day 1': [...], 'Day 2': [...]}
    New Structure:
    {
       'schedule': {'Day 1': [...], 'Day 2': [...]},
       'progress': {'Day 1': False, 'Day 2': False}
    }
    """
    # 1. Create the progress map based on the keys (days)
    progress_map = {}
    for day_key in schedule_data.keys():
        progress_map[day_key] = False  # Default to Not Done

    # 2. restructure
    final_json = {
        "schedule": schedule_data,
        "progress": progress_map
    }

    return final_json