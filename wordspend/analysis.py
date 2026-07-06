"""Regression and residual-predictor analysis for aligned translations."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error, r2_score

from .textstats import count_characters, count_tokens, estimate_syllables, normalize_text

TOKEN_PATTERN = r"(?u)\b\w+\b"


def _empty_result(message: str) -> dict[str, Any]:
    return {
        "available": False,
        "message": message,
        "metrics": {},
        "segments": pd.DataFrame(),
        "source_predictors": pd.DataFrame(),
        "target_predictors": pd.DataFrame(),
    }


def _metric_column(metric: str, side: str) -> str:
    metric = metric.lower()
    if metric in {"token", "tokens", "word", "words"}:
        return f"{side}_token_count"
    if metric in {"char", "chars", "character", "characters"}:
        return f"{side}_char_count"
    if metric in {"syllable", "syllables"}:
        return f"{side}_syllable_count"
    raise ValueError(f"Unsupported metric: {metric}")


def prepare_segments(frame: pd.DataFrame, metric: str = "tokens") -> pd.DataFrame:
    """Return a clean segment frame with source and target length columns."""
    required = {"source_text", "target_text"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df = frame.copy()
    for column in ["work_slug", "work_title", "segment_ref", "source_language", "target_language"]:
        if column not in df.columns:
            df[column] = ""
    if "aligned_segment_id" not in df.columns:
        df["aligned_segment_id"] = np.arange(1, len(df) + 1)

    df["source_text"] = df["source_text"].map(normalize_text)
    df["target_text"] = df["target_text"].map(normalize_text)
    df = df[(df["source_text"].str.strip() != "") & (df["target_text"].str.strip() != "")].copy()

    if "source_token_count" not in df.columns:
        df["source_token_count"] = df["source_text"].map(count_tokens)
    if "target_token_count" not in df.columns:
        df["target_token_count"] = df["target_text"].map(count_tokens)
    if "source_char_count" not in df.columns:
        df["source_char_count"] = df["source_text"].map(count_characters)
    if "target_char_count" not in df.columns:
        df["target_char_count"] = df["target_text"].map(count_characters)
    if "source_syllable_count" not in df.columns:
        df["source_syllable_count"] = df.apply(
            lambda row: estimate_syllables(row["source_text"], row.get("source_language", "")),
            axis=1,
        )
    if "target_syllable_count" not in df.columns:
        df["target_syllable_count"] = df.apply(
            lambda row: estimate_syllables(row["target_text"], row.get("target_language", "English")),
            axis=1,
        )

    source_col = _metric_column(metric, "source")
    target_col = _metric_column(metric, "target")
    df["source_length"] = pd.to_numeric(df[source_col], errors="coerce")
    df["target_length"] = pd.to_numeric(df[target_col], errors="coerce")
    df = df[(df["source_length"] > 0) & (df["target_length"] > 0)].copy()
    return df.reset_index(drop=True)


def fit_length_baseline(df: pd.DataFrame, baseline: str = "log") -> tuple[LinearRegression, np.ndarray, np.ndarray, np.ndarray]:
    """Fit the source-to-target length baseline."""
    x_raw = df["source_length"].to_numpy(dtype=float).reshape(-1, 1)
    y_raw = df["target_length"].to_numpy(dtype=float)
    if baseline == "log":
        x = np.log1p(x_raw)
        y = np.log1p(y_raw)
    elif baseline == "linear":
        x = x_raw
        y = y_raw
    else:
        raise ValueError(f"Unsupported baseline: {baseline}")

    model = LinearRegression()
    model.fit(x, y)
    expected_model_space = model.predict(x)
    residuals = y - expected_model_space
    if baseline == "log":
        expected_target = np.expm1(expected_model_space)
    else:
        expected_target = expected_model_space
    return model, expected_model_space, expected_target, residuals


def _top_examples_from_indices(df: pd.DataFrame, row_indices: np.ndarray, limit: int = 5) -> list[dict[str, Any]]:
    rows = []
    for row_index in row_indices:
        row = df.iloc[int(row_index)]
        rows.append(
            {
                "work_slug": row.get("work_slug", ""),
                "segment_ref": row.get("segment_ref", ""),
                "residual": float(row.get("residual", 0.0)),
            }
        )
    rows.sort(key=lambda item: abs(item["residual"]), reverse=True)
    return rows[:limit]


def calculate_residual_predictors(
    df: pd.DataFrame,
    *,
    side: str,
    top_n: int = 40,
    min_df: int = 2,
    max_features: int = 2000,
    alpha: float = 10.0,
) -> tuple[pd.DataFrame, int, float | None]:
    """Fit a regularised lexical model over residuals."""
    text_col = "source_text" if side == "source" else "target_text"
    if len(df) < 5:
        return pd.DataFrame(), 0, None

    vectorizer = CountVectorizer(
        binary=True,
        lowercase=True,
        max_features=max_features,
        min_df=min_df,
        ngram_range=(1, 2),
        token_pattern=TOKEN_PATTERN,
        strip_accents=None,
    )
    try:
        matrix = vectorizer.fit_transform(df[text_col])
    except ValueError:
        return pd.DataFrame(), 0, None

    feature_names = vectorizer.get_feature_names_out()
    if len(feature_names) == 0:
        return pd.DataFrame(), 0, None

    residuals = df["residual"].to_numpy(dtype=float)
    model = Ridge(alpha=alpha)
    model.fit(matrix, residuals)
    predicted = model.predict(matrix)
    predictor_r2 = float(r2_score(residuals, predicted)) if len(residuals) > 1 else None

    feature_to_index = {feature: idx for idx, feature in enumerate(feature_names)}
    counts = np.asarray(matrix.sum(axis=0)).reshape(-1)
    total_residual = float(np.sum(residuals))
    residual_sums = np.asarray(matrix.T @ residuals).reshape(-1)
    rows = []
    for feature, idx in feature_to_index.items():
        count = int(counts[idx])
        if count <= 0:
            continue
        absent_count = len(df) - count
        with_mean = float(residual_sums[idx] / count)
        without_mean = float((total_residual - residual_sums[idx]) / absent_count) if absent_count else float(np.mean(residuals))
        rows.append(
            {
                "side": side,
                "feature": feature,
                "coefficient": float(model.coef_[idx]),
                "segment_count": count,
                "mean_residual_with_feature": with_mean,
                "mean_residual_without_feature": without_mean,
                "example_refs": _top_examples_from_indices(df, matrix[:, idx].nonzero()[0]),
            }
        )

    predictors = pd.DataFrame(rows)
    if predictors.empty:
        return predictors, int(len(feature_names)), predictor_r2
    predictors["abs_coefficient"] = predictors["coefficient"].abs()
    predictors = predictors.sort_values(["abs_coefficient", "segment_count"], ascending=[False, False])
    return predictors.head(top_n).drop(columns=["abs_coefficient"]).reset_index(drop=True), int(len(feature_names)), predictor_r2


def analyze_translation_spend(
    frame: pd.DataFrame,
    *,
    metric: str = "tokens",
    baseline: str = "log",
    min_segments: int = 5,
    min_df: int = 2,
    top_n: int = 40,
    max_features: int = 2000,
    corpus_label: str = "all",
) -> dict[str, Any]:
    """Run the full baseline and lexical residual analysis."""
    df = prepare_segments(frame, metric=metric)
    if len(df) < min_segments:
        return _empty_result(f"At least {min_segments} aligned segments are required.")

    model, expected_model_space, expected_target, residuals = fit_length_baseline(df, baseline=baseline)
    df["expected_target_length"] = expected_target
    df["residual"] = residuals
    residual_std = float(np.std(residuals))
    df["standardized_residual"] = residuals / residual_std if residual_std else 0.0

    source_predictors, source_feature_count, source_predictor_r2 = calculate_residual_predictors(
        df,
        side="source",
        top_n=top_n,
        min_df=min_df,
        max_features=max_features,
    )
    target_predictors, target_feature_count, target_predictor_r2 = calculate_residual_predictors(
        df,
        side="target",
        top_n=top_n,
        min_df=min_df,
        max_features=max_features,
    )

    source_model_values = np.log1p(df["source_length"].to_numpy(dtype=float).reshape(-1, 1)) if baseline == "log" else df["source_length"].to_numpy(dtype=float).reshape(-1, 1)
    target_model_values = np.log1p(df["target_length"].to_numpy(dtype=float)) if baseline == "log" else df["target_length"].to_numpy(dtype=float)
    predicted_model_values = expected_model_space
    rmse = math.sqrt(mean_squared_error(target_model_values, predicted_model_values))
    r2 = float(r2_score(target_model_values, predicted_model_values))

    metrics = {
        "corpus_label": corpus_label,
        "metric": metric,
        "baseline_model": baseline,
        "feature_space": "surface_unigram_bigram",
        "segment_count": int(len(df)),
        "work_count": int(df["work_slug"].replace("", np.nan).dropna().nunique()),
        "source_length_column": _metric_column(metric, "source"),
        "target_length_column": _metric_column(metric, "target"),
        "intercept": float(model.intercept_),
        "slope": float(model.coef_[0]),
        "r2": r2,
        "rmse": float(rmse),
        "residual_std": residual_std,
        "source_feature_count": int(source_feature_count),
        "target_feature_count": int(target_feature_count),
        "source_predictor_r2": source_predictor_r2,
        "target_predictor_r2": target_predictor_r2,
        "min_df": int(min_df),
        "top_n": int(top_n),
        "max_features": int(max_features),
    }

    return {
        "available": True,
        "message": "",
        "metrics": metrics,
        "segments": df,
        "source_predictors": source_predictors,
        "target_predictors": target_predictors,
    }


def dataframe_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a frame to JSON-safe records."""
    if frame is None or frame.empty:
        return []
    records = []
    for record in frame.replace({np.nan: None}).to_dict(orient="records"):
        clean = {}
        for key, value in record.items():
            if isinstance(value, np.integer):
                clean[key] = int(value)
            elif isinstance(value, np.floating):
                clean[key] = float(value)
            else:
                clean[key] = value
        records.append(clean)
    return records


def write_analysis_outputs(result: dict[str, Any], output_dir: str | Path) -> None:
    """Write metrics, segment residuals, and predictor tables."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    metrics = result.get("metrics", {})
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    segments = result.get("segments", pd.DataFrame())
    predictors_source = result.get("source_predictors", pd.DataFrame())
    predictors_target = result.get("target_predictors", pd.DataFrame())
    if segments is not None and not segments.empty:
        segments.to_csv(output / "segments.csv", index=False)
    else:
        (output / "segments.csv").write_text("", encoding="utf-8")
    if predictors_source is not None and not predictors_source.empty:
        predictors_source.to_csv(output / "source_predictors.csv", index=False)
    else:
        (output / "source_predictors.csv").write_text("", encoding="utf-8")
    if predictors_target is not None and not predictors_target.empty:
        predictors_target.to_csv(output / "target_predictors.csv", index=False)
    else:
        (output / "target_predictors.csv").write_text("", encoding="utf-8")


def load_analysis_outputs(analysis_dir: str | Path) -> dict[str, Any]:
    """Load a previously written analysis directory."""
    root = Path(analysis_dir)
    metrics_path = root / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}

    def read_csv(name: str) -> pd.DataFrame:
        path = root / name
        if not path.exists() or path.stat().st_size == 0:
            return pd.DataFrame()
        return pd.read_csv(path)

    return {
        "available": bool(metrics),
        "message": "" if metrics else "No metrics found.",
        "metrics": metrics,
        "segments": read_csv("segments.csv"),
        "source_predictors": read_csv("source_predictors.csv"),
        "target_predictors": read_csv("target_predictors.csv"),
    }
