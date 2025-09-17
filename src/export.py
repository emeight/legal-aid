import pandas as pd

from pathlib import Path


def export_run_to_excel(run_data: dict, out_path: Path) -> None:
    """Export run_data dictionary to an Excel workbook.

    Parameters
    ----------
    run_data : dict
        Your run_data structure (with 'results' dict inside).

    out_path : Path
        Full path to the .xlsx file to write.

    """
    # results dict from run_data
    results = run_data.get("results", {})
    rows = list(results.values())

    # desired output column order
    desired_cols = [
        "case_number",
        "file_date",
        "init_action",
        "primary_party",
        "defendant",
        "plaintiff",
        "address",
        "zipcode",
    ]

    if not rows:
        df_results = pd.DataFrame(columns=desired_cols)
    else:
        # create DataFrame from rows
        df_results = pd.DataFrame(rows)

        # keep only desired columns, fill in if missing
        df_results = df_results.reindex(columns=desired_cols)

    # metadata
    meta = {
        "started_at": run_data.get("started_at", ""),
        "ended_at": run_data.get("ended_at", ""),
        "time_elapsed": run_data.get("time_elapsed", ""),
        **{f"count_{k}": v for k, v in run_data.get("counts", {}).items()},
    }
    df_meta = pd.DataFrame([meta])

    # write workbook
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as xls:
        df_results.to_excel(xls, sheet_name="results", index=False)
        df_meta.to_excel(xls, sheet_name="run_meta", index=False)
