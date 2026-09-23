"""CGM + Meal Planner Agent.

Takes a glucose (CGM) reading, flags whether it's outside the normal
80-300 mg/dL band, and calls the LLM to produce a same-day 3-meal plan
that respects the patient's dietary preference and medical condition —
adjusting the plan when glucose is out of range.

Guardrails included:
- PLAUSIBLE_LOW / PLAUSIBLE_HIGH: rejects clinically implausible readings
  outright (e.g. 0 mg/dL) instead of building a plan around a likely typo.
- Post-hoc keyword scan for obvious diet violations in the LLM's output
  (e.g. meat mentioned in a vegan plan) — not foolproof, but catches the
  common failure mode of the LLM ignoring the dietary instruction.
"""
from typing import Optional

from llm_client import chat

NORMAL_LOW = 80
NORMAL_HIGH = 300

# Readings outside this wider band are treated as implausible (likely a typo
# or device error) rather than a genuine extreme reading, and are rejected
# before ever reaching the LLM.
PLAUSIBLE_LOW = 40
PLAUSIBLE_HIGH = 400

# Very small, deliberately conservative keyword lists — enough to catch the
# common LLM slip-up (suggesting meat to a vegan/veg patient), not a full
# nutrition-safety system.
_DIET_FORBIDDEN_TERMS = {
    "vegan": [
        "chicken", "beef", "pork", "bacon", "turkey", "lamb", "fish",
        "shrimp", "prawn", "salmon", "tuna", "egg", "cheese", "milk",
        "yogurt", "honey", "butter", "gelatin", "ghee",
    ],
    "veg": [
        "chicken", "beef", "pork", "bacon", "turkey", "lamb", "fish",
        "shrimp", "prawn", "salmon", "tuna", "meat",
    ],
    "non-veg": [],  # no dietary restriction to check
}


def check_glucose(reading: float):
    """Return (in_range: bool, flag_message: str)."""
    if reading < NORMAL_LOW:
        return False, f"⚠️ Reading {reading} mg/dL is LOW (below {NORMAL_LOW}). Plan will favor a quick, balanced meal to raise glucose safely."
    if reading > NORMAL_HIGH:
        return False, f"⚠️ Reading {reading} mg/dL is HIGH (above {NORMAL_HIGH}). Plan will favor low-glycemic, lower-carb meals."
    return True, f"✅ Reading {reading} mg/dL is within the normal 80-300 mg/dL range."


def is_plausible(reading: float) -> bool:
    """Reject readings so extreme they're more likely a typo/device error
    than a genuine value (separate from the 80-300 'normal' band check)."""
    return PLAUSIBLE_LOW <= reading <= PLAUSIBLE_HIGH


# Plant-based phrases that legitimately contain a forbidden substring
# (e.g. "milk" inside "almond milk") and should not trigger a false positive.
_VEGAN_SAFE_PHRASES = [
    "almond milk", "soy milk", "oat milk", "coconut milk", "cashew milk",
    "rice milk", "hemp milk", "pea milk", "plant milk", "plant-based milk",
    "vegan cheese", "vegan butter", "nutritional yeast",
]


def _check_diet_compliance(meal_plan_text: str, dietary_preference: str) -> Optional[str]:
    """Scan the LLM's output for obvious violations of the stated diet.
    Returns a warning string if a forbidden term is found, else None.

    Plant-based phrases (e.g. "soy milk", "almond milk") are stripped out
    before scanning, so they don't trigger a false positive on the bare
    substring "milk" — a known limitation of simple keyword matching.
    """
    forbidden = _DIET_FORBIDDEN_TERMS.get(dietary_preference.strip().lower(), [])
    if not forbidden:
        return None
    lower_text = meal_plan_text.lower()
    for safe_phrase in _VEGAN_SAFE_PHRASES:
        lower_text = lower_text.replace(safe_phrase, "")
    hits = sorted({term for term in forbidden if term in lower_text})
    if not hits:
        return None
    return (
        f"⚠️ Heads up: this plan mentions '{', '.join(hits)}', which may not fit a "
        f"'{dietary_preference}' diet. Please double-check before relying on it — "
        "the meal plan text below was AI-generated and not independently verified."
    )


def build_meal_plan(first_name: str, dietary_preference: str, medical_condition: str, reading: float) -> str:
    if not is_plausible(reading):
        return (
            f"❌ A reading of {reading} mg/dL is outside the plausible range "
            f"({PLAUSIBLE_LOW}-{PLAUSIBLE_HIGH} mg/dL) for a live CGM value. "
            "Please double-check the number and re-enter it — no meal plan was generated."
        )

    in_range, flag_message = check_glucose(reading)

    adjustment = (
        "The glucose reading is within range, so keep the meals balanced and varied."
        if in_range
        else (
            "The glucose reading is OUT OF RANGE — adjust the meal plan accordingly "
            "(e.g. lower glycemic-index choices and controlled carb portions for a high reading, "
            "or a fast-acting balanced meal for a low reading)."
        )
    )

    system_prompt = (
        "You are a cautious nutrition assistant for a healthcare demo app using only synthetic data. "
        "You are not a doctor and you must not give medical diagnoses. "
        "Strictly respect the patient's stated dietary preference — never suggest a food outside it. "
        "Produce a same-day 3-meal plan (breakfast, lunch, dinner) as a short, clearly formatted list."
    )
    user_prompt = (
        f"Patient: {first_name}\n"
        f"Dietary preference: {dietary_preference}\n"
        f"Medical condition: {medical_condition}\n"
        f"Current CGM reading: {reading} mg/dL\n"
        f"{adjustment}\n\n"
        "Give a same-day 3-meal plan (breakfast, lunch, dinner) respecting the dietary preference "
        "and medical condition. Keep it concise, one or two lines per meal."
    )

    meal_plan_text = chat(system_prompt, user_prompt)

    diet_warning = _check_diet_compliance(meal_plan_text, dietary_preference)
    parts = [flag_message]
    if diet_warning:
        parts.append(diet_warning)
    parts.append(meal_plan_text)
    parts.append("_This meal plan is AI-generated demo content using synthetic data — not medical advice._")
    return "\n\n".join(parts)