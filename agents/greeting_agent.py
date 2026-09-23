"""Greeting Agent: looks up a user ID in the dataset and greets them by name."""
import pandas as pd


def load_patients(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["user_id"] = df["user_id"].astype(int)
    return df


def greet(df: pd.DataFrame, user_id: int):
    """Return (success, message_or_record).

    On success, message_or_record is the patient's row (as a dict).
    On failure, message_or_record is a re-prompt string.
    """
    match = df[df["user_id"] == int(user_id)]
    if match.empty:
        return False, f"I couldn't find a patient with ID {user_id}. Please try a valid ID between 1 and {df['user_id'].max()}."
    record = match.iloc[0].to_dict()
    return True, record
