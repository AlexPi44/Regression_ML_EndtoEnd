"""
Feature engineering: date parts, frequency encoding, target encoding, drop leakage.

- Reads cleaned train/eval CSVs
- Applies feature engineering
- Saves feature-engineered CSVs
- ALSO saves fitted encoders for inference
"""

from pathlib import Path
import pandas as pd
from category_encoders import TargetEncoder
from joblib import dump

PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ---------- feature functions ----------

def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    # place after date for readability (optional)
    df.insert(1, "year", df.pop("year"))
    df.insert(2, "quarter", df.pop("quarter"))
    df.insert(3, "month", df.pop("month"))
    return df


def frequency_encode(train: pd.DataFrame, eval: pd.DataFrame, col: str):
    freq_map = train[col].value_counts()
    train[f"{col}_freq"] = train[col].map(freq_map)
    eval[f"{col}_freq"] = eval[col].map(freq_map).fillna(0)
    return train, eval, freq_map


def target_encode(train: pd.DataFrame, eval: pd.DataFrame, col: str, target: str):
    te = TargetEncoder(cols=[col])
    train[f"{col}_encoded"] = te.fit_transform(train[col], train[target])
    eval[f"{col}_encoded"] = te.transform(eval[col])
    return train, eval, te


def drop_unused_columns(train: pd.DataFrame, eval: pd.DataFrame):
    drop_cols = ["date", "city_full", "city", "zipcode", "median_sale_price"]
    train = train.drop(columns=[c for c in drop_cols if c in train.columns], errors="ignore")
    eval = eval.drop(columns=[c for c in drop_cols if c in eval.columns], errors="ignore")
    return train, eval


# ---------- pipeline ----------

def run_feature_engineering(
    in_train_path: Path | str | None = None,
    in_eval_path: Path | str | None = None,
    output_dir: Path | str = PROCESSED_DIR,
):
    """
    Run feature engineering and write outputs + encoders to disk.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Defaults for inputs
    if in_train_path is None:
        in_train_path = PROCESSED_DIR / "cleaning_train.csv"
    if in_eval_path is None:
        in_eval_path = PROCESSED_DIR / "cleaning_eval.csv"

    train_df = pd.read_csv(in_train_path)
    eval_df = pd.read_csv(in_eval_path)

    print("Train date range:", train_df["date"].min(), "to", train_df["date"].max())
    print("Eval date range:", eval_df["date"].min(), "to", eval_df["date"].max())

    # Date features
    train_df = add_date_features(train_df)
    eval_df = add_date_features(eval_df)

    # Frequency encode zipcode (if present)
    freq_map = None
    if "zipcode" in train_df.columns and "zipcode" in eval_df.columns:
        train_df, eval_df, freq_map = frequency_encode(train_df, eval_df, "zipcode")
        dump(freq_map, MODELS_DIR / "freq_encoder.pkl")   # save mapping

    # Target encode city_full (if present)
    target_encoder = None
    if "city_full" in train_df.columns and "city_full" in eval_df.columns:
        train_df, eval_df, target_encoder = target_encode(train_df, eval_df, "city_full", "price")
        dump(target_encoder, MODELS_DIR / "target_encoder.pkl")  # save encoder

    # Drop leakage / raw categoricals
    train_df, eval_df = drop_unused_columns(train_df, eval_df)

    # Save engineered data
    out_train_path = output_dir / "feature_engineered_train.csv"
    out_eval_path = output_dir / "feature_engineered_eval.csv"
    train_df.to_csv(out_train_path, index=False)
    eval_df.to_csv(out_eval_path, index=False)

    print("✅ Feature engineering complete.")
    print("   Train shape:", train_df.shape)
    print("   Eval  shape:", eval_df.shape)
    print("   Encoders saved to models/")

    return train_df, eval_df, freq_map, target_encoder


if __name__ == "__main__":
    run_feature_engineering()
