from __future__ import annotations

import numpy as np
import pandas as pd


def leaderboard(scores: pd.DataFrame, gameweek: int | None = None) -> pd.DataFrame:
    data = scores if gameweek is None else scores[scores["gameweek"] == gameweek]
    latest = int(data["gameweek"].max())
    current = data[data["gameweek"] == latest].copy()
    current = current.sort_values(["cumulative_points", "manager"], ascending=[False, True])
    leader = float(current["cumulative_points"].max())
    current["points_behind_leader"] = leader - current["cumulative_points"]
    if latest > int(scores["gameweek"].min()):
        previous = scores[scores["gameweek"] == latest - 1].set_index("manager")["league_position"]
        current["previous_position"] = current["manager"].map(previous)
        current["movement"] = current["previous_position"] - current["league_position"]
    else:
        current["previous_position"] = np.nan
        current["movement"] = np.nan
    return current


def gameweek_leaderboard(scores: pd.DataFrame, gameweek: int) -> pd.DataFrame:
    frame = scores[scores["gameweek"] == gameweek].copy()
    frame["podium_rank"] = frame["podium_points"].rank(method="min", ascending=False).astype("Int64")
    return frame.sort_values(["podium_points", "manager"], ascending=[False, True])


def streaks(scores: pd.DataFrame) -> pd.DataFrame:
    records = []
    weekly_average = scores.groupby("gameweek")["podium_points"].mean()
    for manager, frame in scores.groupby("manager"):
        frame = frame.sort_values("gameweek")
        flags = [
            1 if points > weekly_average.loc[gw] else -1 if points < weekly_average.loc[gw] else 0
            for gw, points in zip(frame["gameweek"], frame["podium_points"])
        ]
        best_above = best_below = current = 0
        running_above = running_below = 0
        for flag in flags:
            running_above = running_above + 1 if flag == 1 else 0
            running_below = running_below + 1 if flag == -1 else 0
            best_above = max(best_above, running_above)
            best_below = max(best_below, running_below)
        for flag in reversed(flags):
            if flag == 0:
                break
            if current == 0:
                current = flag
                current_length = 1
            elif flag == current:
                current_length += 1
            else:
                break
        else:
            current_length = len(flags)
        if not flags or flags[-1] == 0:
            current = 0
            current_length = 0
        records.append({
            "manager": manager,
            "longest_above": best_above,
            "longest_below": best_below,
            "current_streak_type": "above" if current == 1 else "below" if current == -1 else "none",
            "current_streak": current_length,
        })
    return pd.DataFrame(records)


def longest_winning_streaks(scores: pd.DataFrame) -> pd.DataFrame:
    ranks = scores.copy()
    ranks["podium_rank"] = ranks.groupby("gameweek")["podium_points"].rank(method="min", ascending=False)
    records = []
    for manager, frame in ranks.groupby("manager"):
        running = best = 0
        for won in frame.sort_values("gameweek")["podium_rank"].eq(1):
            running = running + 1 if won else 0
            best = max(best, running)
        records.append({"manager": manager, "longest_winning_streak": best})
    return pd.DataFrame(records)


def comeback_table(scores: pd.DataFrame) -> pd.DataFrame:
    cumulative = scores.pivot(index="gameweek", columns="manager", values="cumulative_points").sort_index()
    gaps = cumulative.rsub(cumulative.max(axis=1), axis=0)
    start = gaps.iloc[0]
    end = gaps.iloc[-1]
    previous = gaps.iloc[-2] if len(gaps) > 1 else start
    return pd.DataFrame({
        "manager": gaps.columns,
        "initial_deficit": start.values,
        "previous_deficit": previous.values,
        "latest_deficit": end.values,
        "points_recovered": previous.values - end.values,
        "total_recovered": start.values - end.values,
    }).sort_values("points_recovered", ascending=False)


def title_race(scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pivot = scores.pivot(index="gameweek", columns="manager", values="cumulative_points").sort_index()
    first_second = []
    for week, row in pivot.iterrows():
        ordered = row.sort_values(ascending=False)
        first_second.append({
            "gameweek": week,
            "gap": float(ordered.iloc[0] - ordered.iloc[1]) if len(ordered) > 1 else 0.0,
        })
    return pivot, pd.DataFrame(first_second)


def simulate_season(scores: pd.DataFrame, simulations: int = 10_000, seed: int = 2026) -> pd.DataFrame:
    latest_week = int(scores["gameweek"].max())
    remaining = max(0, 38 - latest_week)
    current = scores[scores["gameweek"] == latest_week].set_index("manager")["cumulative_points"]
    managers = current.index.tolist()
    result = np.zeros((simulations, len(managers)), dtype=float)
    rng = np.random.default_rng(seed)
    for index, manager in enumerate(managers):
        history = scores.loc[scores["manager"] == manager, "adjusted_gw_points"].to_numpy(dtype=float)
        samples = rng.choice(history, size=(simulations, remaining), replace=True) if remaining else np.empty((simulations, 0))
        result[:, index] = float(current[manager]) + samples.sum(axis=1)
    first = np.zeros(len(managers), dtype=float)
    top_three = np.zeros(len(managers), dtype=float)
    for simulated_points in result:
        winners = np.flatnonzero(simulated_points == simulated_points.max())
        first[winners] += 1 / len(winners)
        ranks = pd.Series(simulated_points).rank(method="min", ascending=False).to_numpy()
        top_three[ranks <= 3] += 1
    return pd.DataFrame({
        "manager": managers,
        "projected_mean": result.mean(axis=0),
        "projected_median": np.median(result, axis=0),
        "title_probability": first / simulations * 100,
        "top_three_probability": top_three / simulations * 100,
    }).sort_values("projected_mean", ascending=False)
