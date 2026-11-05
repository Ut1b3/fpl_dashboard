# FPL Mini-League Analytics Dashboard

Interactive Streamlit and Plotly analytics for a 14-manager Fantasy Premier League mini-league.

## What is included

- Ten dashboard views: overview, historical position, performance, title race, manager comparison, Gameweek centre, podiums, chips, records and projections.
- A centralized Excel ingestion and scoring layer, with validated league standings, actual-score podiums and chip-adjusted cumulative totals.
- CSV download for the overview leaderboard, interactive Plotly visualisations, and 10,000 resampled season simulations.
- Data quality notices for partial Gameweeks, name mismatches and missing chip details.

## Scoring and validation

`FPL Points.xlsx` is the Gameweek score source (including any chip bonus) and its `Total` column is a reconciliation reference. The chips workbook records the extra points each chip added. For every used Triple Captain or Bench Boost, the dashboard derives:

`podium points = workbook Gameweek score - chip extra points`

`adjusted Gameweek points = workbook Gameweek score = podium points + chip bonus`

Example: a manager who would have scored 50 and scores 75 with a Triple Captain has 25 chip points. Their total points include all 75, but podium places use 50.

Totals and league positions include chip points; podium and Gameweek-winner analytics exclude them.

Ties in overall standings use shared competition ranking (`1, 1, 3`). Tables use manager name as a stable display sort when points tie. For the podium mini-competition, managers tied across podium places split the points for the occupied places; ties extending beyond third receive no award.

Performance and podium analytics use chip-free actual points. Overall positions and totals use adjusted points. Blank future Gameweeks are excluded; only fully populated Gameweeks are treated as completed.

## Local setup

Requires Python 3.11 or newer.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`).

## Updating the data

Replace `data/FPL Points.xlsx` and `data/FPL Chips.xlsx` with updated versions, keeping the sheet headers and manager names consistent. On Streamlit Community Cloud, commit and push the revised files to GitHub; the app's cache key incorporates file modification time and size, so a repository update refreshes the loaded data.

To add a Gameweek, populate its `GW n` column for every manager. A partially populated column is excluded and shown as a validation notice. The `Total` column should remain the cumulative adjusted points and is checked, not added a second time.

For a used Triple Captain or Bench Boost, enter the deployment as `GWn` in the relevant `... used` field and the extra points the chip added in its points field. The Gameweek column of the points workbook keeps the full score including the chip.

Google Sheets can be added later by replacing the file-reading boundary in `utils/data_loader.py`; the rest of the analytics uses the normalized `DashboardData` structure.

## Automated tests

```powershell
pytest -q
```

## Deploy publicly with GitHub and Streamlit Community Cloud

1. Create a GitHub repository and upload this project, including the two files in `data/`.
2. Keep workbook data limited to information intended to be public; this dashboard does not provide an administrator upload interface or require secrets.
3. Visit [Streamlit Community Cloud](https://share.streamlit.io/), sign in with GitHub, and select **Create app**.
4. Choose the repository, branch, and `app.py` as the entry point; set Python to 3.11 or newer if the deployment UI offers a version setting.
5. Deploy. The resulting `*.streamlit.app` URL is publicly viewable and can be shared.
6. To publish updated scores, replace the workbooks in `data/`, commit and push the changes; Streamlit Community Cloud rebuilds the app.

## Project layout

```text
app.py
requirements.txt
data/
  FPL Points.xlsx
  FPL Chips.xlsx
utils/
  data_loader.py
  calculations.py
  chart_helpers.py
views/
  overview.py
  position_trend.py
  performance.py
  cumulative.py
  comparison.py
  gameweek.py
  podium.py
  chips.py
  records.py
  projections.py
tests/
.streamlit/config.toml
```
