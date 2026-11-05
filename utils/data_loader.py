from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


GAMEWEEK_PATTERN = re.compile(r"^GW\s*(\d+)$", re.IGNORECASE)


@dataclass
class DashboardData:
    scores: pd.DataFrame
    chips: pd.DataFrame
    stats: pd.DataFrame
    podium_table: pd.DataFrame
    validation: list[str]
    managers: list[str]
    completed_gameweeks: list[int]
    updated_at: pd.Timestamp


def _column_map(frame: pd.DataFrame) -> dict[str, Any]:
    return {str(column).strip().casefold(): column for column in frame.columns}


def _gameweek_columns(frame: pd.DataFrame) -> dict[int, Any]:
    columns: dict[int, Any] = {}
    for column in frame.columns:
        match = GAMEWEEK_PATTERN.match(str(column).strip())
        if match:
            columns[int(match.group(1))] = column
    return columns


def _clean_manager(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_gameweek(value: Any) -> int | None:
    match = re.search(r"\bGW\s*(\d+)\b", str(value), re.IGNORECASE)
    return int(match.group(1)) if match else None


def _is_used(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return value
    text = str(value).strip().casefold()
    return text not in {"", "n/a", "na", "no", "unused", "not used", "false", "none", "0", "nan"}


def _numeric(value: Any) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)


def _chip_rows(chip_frame: pd.DataFrame, managers: list[str]) -> pd.DataFrame:
    columns = _column_map(chip_frame)
    manager_column = chip_frame.columns[0]
    definitions = [
        ("triple_cap", 1, "triple cap 1 used", "triple cap gw actual points"),
        ("bench_boost", 1, "bench boost 1 used", "bench boost 1 points"),
        ("triple_cap", 2, "triple cap 2 used", "triple cap 2 points"),
        ("bench_boost", 2, "bench boost 2 used", "bench boost 2 points"),
    ]
    manager_lookup = {name.casefold(): name for name in managers}
    records: list[dict[str, Any]] = []
    for _, row in chip_frame.iterrows():
        raw_name = _clean_manager(row[manager_column])
        manager = manager_lookup.get(raw_name.casefold(), raw_name)
        if not manager:
            continue
        for chip_type, number, used_key, points_key in definitions:
            used_column = columns.get(used_key)
            points_column = columns.get(points_key)
            used_value = row[used_column] if used_column is not None else None
            points_value = row[points_column] if points_column is not None else None
            used = _is_used(used_value)
            status = "review: deployment column missing" if used_column is None else "used" if used else "unused"
            records.append({
                "manager": manager,
                "chip_type": chip_type,
                "chip_number": number,
                "gameweek": _parse_gameweek(used_value) if used else None,
                "actual_points": _numeric(points_value),
                "chip_bonus": np.nan,
                "usage_status": status,
            })
    return pd.DataFrame(records)


def load_dashboard_data(points_path: str | Path, chips_path: str | Path) -> DashboardData:
    points_frame = pd.read_excel(points_path, engine="openpyxl")
    chip_frame = pd.read_excel(chips_path, engine="openpyxl")
    if points_frame.empty or len(points_frame.columns) < 2:
        raise ValueError("The points workbook must contain managers and Gameweek columns.")
    if chip_frame.empty or len(chip_frame.columns) < 2:
        raise ValueError("The chips workbook must contain manager and chip columns.")

    manager_column = points_frame.columns[0]
    points_frame[manager_column] = points_frame[manager_column].map(_clean_manager)
    if (points_frame[manager_column] == "").any():
        raise ValueError("The points workbook contains a blank manager name.")
    duplicates = points_frame[manager_column].duplicated(keep=False)
    casefolded = points_frame[manager_column].str.casefold()
    duplicates = duplicates | casefolded.duplicated(keep=False)
    if duplicates.any():
        names = sorted(points_frame.loc[duplicates, manager_column].unique())
        raise ValueError(f"Duplicate manager names in points workbook: {', '.join(names)}")
    managers = points_frame[manager_column].tolist()
    manager_set = {name.casefold() for name in managers}
    chip_manager_column = chip_frame.columns[0]
    chip_names = chip_frame[chip_manager_column].map(_clean_manager)
    if chip_names.duplicated(keep=False).any():
        names = sorted(chip_names[chip_names.duplicated(keep=False)].unique())
        raise ValueError(f"Duplicate manager names in chips workbook: {', '.join(names)}")
    unknown_chips = sorted(name for name in chip_names if name and name.casefold() not in manager_set)
    missing_chips = sorted(set(managers) - {name for name in chip_names if name})
    validation: list[str] = []
    if unknown_chips:
        validation.append(f"Chip workbook has unknown managers: {', '.join(unknown_chips)}.")
    if missing_chips:
        validation.append(f"Managers missing from chip workbook: {', '.join(missing_chips)}.")

    gw_columns = _gameweek_columns(points_frame)
    if not gw_columns:
        raise ValueError("No columns named GW 1, GW 2, etc. were found in the points workbook.")
    completed: list[int] = []
    partial: list[int] = []
    for gameweek in sorted(gw_columns):
        values = pd.to_numeric(points_frame[gw_columns[gameweek]], errors="coerce")
        if values.notna().all():
            completed.append(gameweek)
        elif values.notna().any():
            partial.append(gameweek)
    if partial:
        validation.append(
            "Partially populated Gameweeks excluded from completed results: "
            + ", ".join(f"GW{week}" for week in partial)
            + "."
        )
    expected = list(range(1, max(completed, default=0) + 1))
    if completed != expected:
        validation.append("Completed Gameweeks contain a gap; standings include only fully populated weeks.")

    chips = _chip_rows(chip_frame, managers)
    if "total" not in _column_map(points_frame):
        validation.append("Points workbook has no Total column; cumulative reconciliation is unavailable.")

    records: list[dict[str, Any]] = []
    for _, row in points_frame.iterrows():
        manager = row[manager_column]
        for gameweek in completed:
            score = float(pd.to_numeric(row[gw_columns[gameweek]], errors="raise"))
            records.append({
                "manager": manager,
                "gameweek": gameweek,
                "podium_points": score,
                "chip_bonus": 0.0,
                "adjusted_gw_points": score,
            })
    scores = pd.DataFrame(records)
    score_index = {(row.manager, int(row.gameweek)): index for index, row in scores.iterrows()}

    for chip_index, chip in chips.iterrows():
        if chip["usage_status"].startswith("review"):
            validation.append(f"{chip['manager']}: {chip['chip_type']} {chip['chip_number']} {chip['usage_status'][8:]}.")
            continue
        if chip["usage_status"] != "used":
            continue
        manager = chip["manager"]
        gameweek = chip["gameweek"]
        if pd.isna(gameweek):
            chips.at[chip_index, "usage_status"] = "review: gameweek missing"
            validation.append(f"{manager}: {chip['chip_type']} {chip['chip_number']} is marked used without a Gameweek.")
            continue
        key = (manager, int(gameweek))
        if key not in score_index:
            chips.at[chip_index, "usage_status"] = "review: score unavailable"
            validation.append(f"{manager}: {chip['chip_type']} at GW{gameweek} has no completed score.")
            continue
        score_row = score_index[key]
        workbook_score = float(scores.at[score_row, "adjusted_gw_points"])
        chip_name = "Triple Captain" if chip["chip_type"] == "triple_cap" else "Bench Boost"
        # The chip points column holds the extra points the chip added to the Gameweek.
        bonus = chip["actual_points"]
        if pd.isna(bonus):
            scores.at[score_row, "podium_points"] = np.nan
            chips.at[chip_index, "usage_status"] = "review: chip points missing"
            validation.append(f"{manager}: {chip_name} at GW{gameweek} is missing its extra chip points.")
            continue
        if bonus < 0 or bonus > workbook_score:
            scores.at[score_row, "podium_points"] = np.nan
            chips.at[chip_index, "usage_status"] = "review: inconsistent score"
            validation.append(
                f"{manager}: {chip_name} at GW{gameweek} records {bonus:g} extra points, "
                f"outside the workbook score of {workbook_score:g}."
            )
            continue
        if not pd.isna(scores.at[score_row, "podium_points"]):
            scores.at[score_row, "podium_points"] -= bonus
        chips.at[chip_index, "chip_bonus"] = bonus

    # Keep the source workbook score as the final adjusted total; derive the bonus
    # after chip-free scores are substituted so scoring is never added twice.
    scores["chip_bonus"] = scores["adjusted_gw_points"] - scores["podium_points"]
    if scores["chip_bonus"].lt(0).any():
        raise ValueError("Chip processing produced a negative adjustment.")
    scores = scores.sort_values(["gameweek", "manager"]).reset_index(drop=True)
    scores["cumulative_points"] = scores.groupby("manager")["adjusted_gw_points"].cumsum()
    scores["league_position"] = (
        scores.groupby("gameweek")["cumulative_points"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    point_columns = _column_map(points_frame)
    total_column = point_columns.get("total")
    if total_column is not None:
        source_totals = points_frame.set_index(manager_column)[total_column]
        calculated = scores.groupby("manager")["adjusted_gw_points"].sum()
        for manager in managers:
            source_total = _numeric(source_totals.loc[manager])
            if source_total is None:
                continue
            calc_total = float(calculated.get(manager, 0))
            if not np.isclose(source_total, calc_total):
                validation.append(
                    f"{manager}: Total column {source_total:g} does not match calculated "
                    f"completed-GW total {calc_total:g}."
                )

    podium_table = _build_podium_table(scores, managers)
    stats = _build_manager_stats(scores, podium_table, managers, chips)
    updated_at = max(Path(points_path).stat().st_mtime, Path(chips_path).stat().st_mtime)
    updated = pd.Timestamp(updated_at, unit="s")
    return DashboardData(scores, chips, stats, podium_table, validation, managers, completed, updated)


def _build_podium_table(scores: pd.DataFrame, managers: list[str]) -> pd.DataFrame:
    awards: dict[str, dict[str, float]] = {
        manager: {"podium_points": 0.0, "wins": 0, "seconds": 0, "thirds": 0, "appearances": 0}
        for manager in managers
    }
    for _, group in scores.groupby("gameweek"):
        ranked = group.assign(rank=group["podium_points"].rank(method="min", ascending=False))
        for _, row in ranked.iterrows():
            if pd.isna(row["rank"]):
                continue
            rank = int(row["rank"])
            if rank > 3:
                continue
            tied = ranked[ranked["rank"] == rank]
            places = list(range(rank, min(3, rank + len(tied) - 1) + 1))
            award = sum({1: 3, 2: 2, 3: 1}[place] for place in places) / len(tied)
            entry = awards[row["manager"]]
            entry["podium_points"] += award
            entry["appearances"] += 1
            if rank == 1:
                entry["wins"] += 1
            if rank <= 2 and rank + len(tied) - 1 >= 2:
                entry["seconds"] += 1 / len(tied)
            if rank <= 3 and rank + len(tied) - 1 >= 3:
                entry["thirds"] += 1 / len(tied)
    return (
        pd.DataFrame.from_dict(awards, orient="index")
        .rename_axis("manager")
        .reset_index()
        .sort_values(["podium_points", "wins", "manager"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def _build_manager_stats(
    scores: pd.DataFrame,
    podium: pd.DataFrame,
    managers: list[str],
    chips: pd.DataFrame,
) -> pd.DataFrame:
    if scores.empty:
        return pd.DataFrame(columns=["manager", "total_points", "average_points"])
    weekly_average = scores.groupby("gameweek")["podium_points"].mean()
    performance = scores.assign(
        above_average=scores["podium_points"] > scores["gameweek"].map(weekly_average),
        below_average=scores["podium_points"] < scores["gameweek"].map(weekly_average),
    )
    summary = performance.groupby("manager").agg(
        total_points=("adjusted_gw_points", "sum"),
        average_points=("podium_points", "mean"),
        median_points=("podium_points", "median"),
        standard_deviation=("podium_points", "std"),
        highest_gw=("podium_points", "max"),
        lowest_gw=("podium_points", "min"),
        above_average_weeks=("above_average", "sum"),
        below_average_weeks=("below_average", "sum"),
    )
    summary["coefficient_of_variation"] = (
        summary["standard_deviation"].fillna(0) / summary["average_points"].replace(0, np.nan)
    )
    # Podium points use actual, chip-free scores; win count is likewise based on them.
    actual_ranks = scores.groupby("gameweek")["podium_points"].rank(method="min", ascending=False)
    wins = scores.assign(actual_rank=actual_ranks).groupby("manager")["actual_rank"].apply(lambda values: int((values == 1).sum()))
    summary["gameweek_wins"] = wins
    podium_stats = podium.set_index("manager")
    for column in ["podium_points", "wins", "seconds", "thirds", "appearances"]:
        summary[column] = podium_stats[column]
    gameweeks = sorted(scores["gameweek"].unique())
    position_history = scores.groupby("manager")["league_position"]
    summary["best_league_position"] = position_history.min()
    summary["worst_league_position"] = position_history.max()
    latest = scores[scores["gameweek"] == max(gameweeks)].set_index("manager")["league_position"]
    summary["current_league_position"] = latest
    summary["unused_chips"] = (
        chips.assign(is_unused=chips["usage_status"].eq("unused"))
        .groupby("manager")["is_unused"].sum()
        .reindex(managers, fill_value=0)
    )
    observed_weeks = scores.groupby("manager")["podium_points"].count()
    summary["above_average_pct"] = (
        summary["above_average_weeks"] / observed_weeks.reindex(summary.index).replace(0, np.nan) * 100
    )
    summary["podium_frequency_pct"] = summary["appearances"] / len(gameweeks) * 100
    return summary.reindex(managers).rename_axis("manager").reset_index()
