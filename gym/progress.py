"""Show progress per exercise: best set and total volume per session.

Usage: python gym/progress.py [exercise filter]
"""
import json
import sys
from pathlib import Path

SESSIONS = Path(__file__).parent / "sessions"


def main(filter_text: str = "") -> None:
    history: dict[str, list[str]] = {}
    for path in sorted(SESSIONS.glob("*.json")):
        session = json.loads(path.read_text())
        for ex in session.get("exercises", []) + session.get("optional_if_gym_is_quiet", []):
            sets = [s for s in ex["sets"] if s.get("kg") is not None]
            if not sets or filter_text.lower() not in ex["name"].lower():
                continue
            best = max(sets, key=lambda s: (s["kg"], s["reps"]))
            volume = sum(s["kg"] * s["reps"] for s in sets) * (2 if ex.get("per_side") else 1)
            history.setdefault(ex["name"], []).append(
                f"  {session['date']}  best {best['kg']} kg x {best['reps']}  "
                f"sets {len(sets)}  volume {volume:.0f} kg"
            )
    for name, rows in history.items():
        print(name)
        print("\n".join(rows))


if __name__ == "__main__":
    main(" ".join(sys.argv[1:]))
