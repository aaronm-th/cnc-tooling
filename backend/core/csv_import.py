import csv
import io
from datetime import datetime

DATE_FORMATS = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]
TIME_FORMATS = ["%H:%M:%S", "%H:%M"]


def _try_parse(value, formats, parse_type):
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.date() if parse_type == "date" else parsed.time()
        except ValueError:
            continue
    return None


def parse_legacy_csv(file_obj):
    """
    Erwartet eine Zeile pro Tag, keine Kopfzeile:
        Spalte 1: Datum (z.B. 01.03.2024)
        Spalte 2: Check-In 1
        Spalte 3: Check-Out 1
        Spalte 4: Check-In 2
        Spalte 5: Check-Out 2
        ... (beliebig viele weitere Check-In/Check-Out-Paare)

    Fehlt bei der letzten Session der Check-Out (ungerade Anzahl an
    Zeit-Spalten), wird das Paar mit check_out=None zurückgegeben.
    Leere Zellen am Zeilenende werden ignoriert.

    Gibt zurück: [(date, [(check_in_time, check_out_time_or_None), ...]), ...]
    """
    decoded = io.TextIOWrapper(file_obj, encoding="utf-8-sig")
    reader = csv.reader(decoded)

    days = []

    for row_num, row in enumerate(reader, start=1):
        if not row or not row[0].strip():
            continue

        date_str = row[0].strip()
        day_date = _try_parse(date_str, DATE_FORMATS, "date")
        if not day_date:
            raise ValueError(f"Zeile {row_num}: Konnte Datum nicht interpretieren: '{date_str}'")

        times = []
        for cell in row[1:]:
            cell = cell.strip()
            if not cell:
                continue
            parsed_time = _try_parse(cell, TIME_FORMATS, "time")
            if not parsed_time:
                raise ValueError(f"Zeile {row_num}: Konnte Zeit nicht interpretieren: '{cell}'")
            times.append(parsed_time)

        pairs = []
        it = iter(times)
        for t_in in it:
            pairs.append((t_in, next(it, None)))

        days.append((day_date, pairs))

    return days