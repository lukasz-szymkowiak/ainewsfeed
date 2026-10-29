# Gym tracker

Goal: lose body weight (108 kg, 183 cm) and keep muscle and strength.

- `sessions/` – one JSON file per workout: `YYYY-MM-DD-<type>.json`. Each set is `{"kg": .., "reps": ..}`.
- `templates.json` – the usual workouts (back, chest/push, legs).
- `profile.json` – body weight and calories log.
- `progress.py` – `python gym/progress.py` (or `python gym/progress.py row`) shows best set and volume over time.

Rule for muscle retention while cutting: keep the weight on the bar. If the top set stays the same or goes up while body weight goes down, the plan works.
