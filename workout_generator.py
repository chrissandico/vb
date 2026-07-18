"""Generate a 30-minute, 6-exercise workout plan by type and email it."""
import random

NUM_EXERCISES = 6
TOTAL_MINUTES = 30
MINUTES_PER_EXERCISE = TOTAL_MINUTES // NUM_EXERCISES


def parse_types(type_field):
    """Split a Type column value like 'Core, Mobility' into ['Core', 'Mobility']."""
    if not type_field:
        return []
    return [t.strip() for t in str(type_field).split(',') if t.strip()]


def select_exercises(all_records, workout_type):
    """Pick NUM_EXERCISES exercises matching workout_type (case-insensitive).

    If fewer than NUM_EXERCISES rows match, randomly repeats matched rows
    (marked with '_repeat': True) to fill the remainder. Raises ValueError
    if zero rows match. Every returned entry is a shallow copy of its source
    row dict, so mutating a returned entry never affects all_records.
    """
    wanted = workout_type.strip().lower()
    matches = [
        r for r in all_records
        if wanted in [t.lower() for t in parse_types(r.get('Type', ''))]
    ]

    if not matches:
        raise ValueError(f"No exercises found with type '{workout_type}'.")

    if len(matches) >= NUM_EXERCISES:
        return [dict(r) for r in random.sample(matches, NUM_EXERCISES)]

    selected = [dict(r) for r in matches]
    pool = list(matches)
    random.shuffle(pool)
    i = 0
    while len(selected) < NUM_EXERCISES:
        repeat = dict(pool[i % len(pool)])
        repeat['_repeat'] = True
        selected.append(repeat)
        i += 1
    random.shuffle(selected)
    return selected
