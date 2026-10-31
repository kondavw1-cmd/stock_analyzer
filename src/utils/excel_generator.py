import logging
import os
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd

logger = logging.getLogger(__name__)


def export_to_excel_direct(
    output_path: str,
    df_scored_results: pd.DataFrame,
    universe_750_df: pd.DataFrame = None,
    open_journal_df: pd.DataFrame = None,
    closed_journal_df: pd.DataFrame = None,
):
    """Creates a stylized multi-tab Excel file directly with custom ACTION colors."""
    logger.info(f"Generating styled Excel report: {output_path} ...")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_blue = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_navy = PatternFill(
        start_color="1F497D", end_color="1F497D", fill_type="solid"
    )
    header_grey = PatternFill(
        start_color="595959", end_color="595959", fill_type="solid"
    )
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )
    zebra_fill = PatternFill(
        start_color="F9FAFB", end_color="F9FAFB", fill_type="solid"
    )

    action_styles = {
        "+ADD": {
            "fill": PatternFill(
                start_color="00B050", end_color="00B050", fill_type="solid"
            ),
            "font": Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
        },
        "HOLD": {
            "fill": PatternFill(
                start_color="0070C0", end_color="0070C0", fill_type="solid"
            ),
            "font": Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
        },
        "REVIEW": {
            "fill": PatternFill(
                start_color="FFD966", end_color="FFD966", fill_type="solid"
            ),
            "font": Font(name="Calibri", size=10, bold=True, color="000000"),
        },
        "REPLACE": {
            "fill": PatternFill(
                start_color="ED7D31", end_color="ED7D31", fill_type="solid"
            ),
            "font": Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
        },
        "EXIT": {
            "fill": PatternFill(
                start_color="FF0000", end_color="FF0000", fill_type="solid"
            ),
            "font": Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
        },
    }

    sheets_to_write = [
        ("Open-Partial-Journal", open_journal_df),
        ("Closed-Journal", closed_journal_df),
        ("Universe-of-750-Stocks-Scores", universe_750_df),
        ("Python-750-Computed-Scores", df_scored_results),
    ]

    for sheet_name, df in sheets_to_write:
        if df is None or df.empty:
            continue

        ws = wb.create_sheet(title=sheet_name)
        ws.views.sheetView[0].showGridLines = True

        headers = list(df.columns)
        ws.append(headers)

        for col_idx, col_name in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )

            if "Temp" in col_name:
                cell.fill = header_navy
            elif col_name in ["ACTION", "REMARKS", "REMAKS"]:
                cell.fill = header_grey
            else:
                cell.fill = header_blue

        for row_idx, row in enumerate(df.itertuples(index=False), 2):
            ws.append(list(row))
            is_even = row_idx % 2 == 0

            for col_idx in range(1, len(headers) + 1):
                col_name = headers[col_idx - 1]
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                if is_even:
                    cell.fill = zebra_fill

                if col_name == "ACTION" and str(cell.value) in action_styles:
                    cell.fill = action_styles[str(cell.value)]["fill"]
                    cell.font = action_styles[str(cell.value)]["font"]
                    cell.alignment = Alignment(
                        horizontal="center", vertical="center"
                    )

                if isinstance(cell.value, (int, float)):
                    if any(
                        k in col_name
                        for k in [
                            "Price",
                            "cost",
                            "LTP",
                            "P&L",
                            "val",
                            "Invested",
                            "SL",
                            "Investment",
                        ]
                    ):
                        cell.number_format = "#,##0.00"
                    elif "%" in col_name or "Ratio" in col_name or "SCORE" in col_name:
                        cell.number_format = "0.00"

        ws.freeze_panes = "A2"

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 11), 38)

        logger.info(f" -> Created sheet: '{sheet_name}' ({len(df)} rows)")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)
    logger.info(f"[Success] Direct Excel report generated and saved to: {output_path}")