import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "You are a running coach assistant. "
    "Provide a brief, factual, concise summary comparing the runner's actual "
    "performance against their planned session. No fluff. Stick to key metrics "
    "and deviations from the plan."
)

WORKOUT_TYPES = {0: "Default", 1: "Race", 2: "Long Run", 3: "Workout"}


class RunningCoachAgent:
    def __init__(self, client: anthropic.Anthropic):
        self.client = client

    def analyze(self, activity: dict, planned_session: dict) -> str:
        prompt = _build_prompt(activity, planned_session)
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


def _pace_str(speed_mps: float) -> str:
    if speed_mps <= 0:
        return "N/A"
    min_per_km = (1 / speed_mps) / 60
    return f"{int(min_per_km)}:{int((min_per_km % 1) * 60):02d} /km"


def _duration_str(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def _build_prompt(activity: dict, planned_session: dict) -> str:
    lines = []

    # --- Plan ---
    lines.append(f"Planned session: {planned_session['planned']}")
    lines.append(f"Session type: {planned_session['session_type']}")

    comments = planned_session.get("athlete_comments", "")
    if comments:
        lines.append(f"Athlete's notes: {comments}")

    description = activity.get("description")
    if description:
        lines.append(f"Activity description: {description}")

    # --- Actual ---
    lines.append("")
    lines.append("Actual activity:")

    distance_km = activity["distance"] / 1000
    moving_time_s = activity["moving_time"]
    workout_label = WORKOUT_TYPES.get(activity.get("workout_type"), "Default")

    lines.append(f"- Type: {activity['sport_type']} ({workout_label})")
    lines.append(f"- Start time (local): {activity['start_date_local'].strftime('%H:%M')}")
    lines.append(f"- Distance: {distance_km:.2f} km")
    lines.append(f"- Moving time: {_duration_str(moving_time_s)} ({moving_time_s} seconds)")
    lines.append(f"- Average pace: {_pace_str(activity['average_speed'])}")
    lines.append(f"- Max speed: {_pace_str(activity['max_speed'])}")

    # Elevation
    if activity.get("total_elevation_gain") is not None:
        lines.append(f"- Elevation gain: {activity['total_elevation_gain']:.0f} m")
    if activity.get("elev_high") is not None and activity.get("elev_low") is not None:
        lines.append(f"- Elevation range: {activity['elev_low']:.0f} – {activity['elev_high']:.0f} m")

    # Heart rate
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    if avg_hr is not None:
        lines.append(f"- Avg heart rate: {avg_hr:.0f} bpm")
    if max_hr is not None:
        lines.append(f"- Max heart rate: {max_hr} bpm")

    # Cadence & power
    if activity.get("average_cadence") is not None:
        lines.append(f"- Cadence: {activity['average_cadence']:.0f} spm")
    if activity.get("average_watts") is not None:
        lines.append(f"- Power: {activity['average_watts']:.0f} W")

    # Environment & effort
    if activity.get("average_temp") is not None:
        lines.append(f"- Temperature: {activity['average_temp']}°C")
    if activity.get("calories") is not None:
        lines.append(f"- Calories: {activity['calories']:.0f} kcal")
    if activity.get("suffer_score") is not None:
        lines.append(f"- Relative effort: {activity['suffer_score']}")
    if activity.get("perceived_exertion") is not None:
        lines.append(f"- Perceived exertion: {activity['perceived_exertion']}/10")

    # Splits
    splits = activity.get("splits_metric")
    if splits:
        lines.append("")
        lines.append("Per-km splits:")
        for s in splits:
            hr_str = f" | HR: {s['average_heartrate']:.0f}" if s["average_heartrate"] else ""
            elev = s["elevation_difference"]
            elev_str = f" | Elev: {'+' if elev >= 0 else ''}{elev:.0f}m"
            lines.append(
                f"  Split {s['split']}: {s['distance'] / 1000:.2f} km"
                f" in {_duration_str(s['moving_time'])}"
                f" | Pace: {_pace_str(s['average_speed'])}"
                f"{hr_str}{elev_str}"
            )

    lines.append("")
    lines.append("Provide a brief factual analysis of how the actual run compares to the plan.")
    return "\n".join(lines)
