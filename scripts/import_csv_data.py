import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.db import get_connection


TABLES = {
    "weather_data": {
        "file_pattern": "weather_data_*.csv",
        "columns": [
            "city",
            "fx_date",
            "sunrise",
            "sunset",
            "moonrise",
            "moonset",
            "moon_phase",
            "moon_phase_icon",
            "temp_max",
            "temp_min",
            "icon_day",
            "text_day",
            "icon_night",
            "text_night",
            "wind360_day",
            "wind_dir_day",
            "wind_scale_day",
            "wind_speed_day",
            "wind360_night",
            "wind_dir_night",
            "wind_scale_night",
            "wind_speed_night",
            "precip",
            "uv_index",
            "humidity",
            "pressure",
            "vis",
            "cloud",
            "update_time",
        ],
        "create_sql": """
            CREATE TABLE IF NOT EXISTS weather_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                city VARCHAR(50) NOT NULL,
                fx_date DATE NOT NULL,
                sunrise TIME,
                sunset TIME,
                moonrise TIME,
                moonset TIME,
                moon_phase VARCHAR(20),
                moon_phase_icon VARCHAR(10),
                temp_max INT,
                temp_min INT,
                icon_day VARCHAR(10),
                text_day VARCHAR(20),
                icon_night VARCHAR(10),
                text_night VARCHAR(20),
                wind360_day INT,
                wind_dir_day VARCHAR(20),
                wind_scale_day VARCHAR(10),
                wind_speed_day INT,
                wind360_night INT,
                wind_dir_night VARCHAR(20),
                wind_scale_night VARCHAR(10),
                wind_speed_night INT,
                precip DECIMAL(5, 1),
                uv_index INT,
                humidity INT,
                pressure INT,
                vis INT,
                cloud INT,
                update_time DATETIME,
                UNIQUE KEY unique_city_date (city, fx_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
              COLLATE=utf8mb4_unicode_ci
        """,
    },
    "train_tickets": {
        "file_pattern": "train_tickets_*.csv",
        "columns": [
            "departure_city",
            "arrival_city",
            "departure_time",
            "arrival_time",
            "train_number",
            "seat_type",
            "total_seats",
            "remaining_seats",
            "price",
            "created_at",
        ],
        "create_sql": """
            CREATE TABLE IF NOT EXISTS train_tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                departure_city VARCHAR(50) NOT NULL,
                arrival_city VARCHAR(50) NOT NULL,
                departure_time DATETIME NOT NULL,
                arrival_time DATETIME NOT NULL,
                train_number VARCHAR(20) NOT NULL,
                seat_type VARCHAR(20) NOT NULL,
                total_seats INT NOT NULL,
                remaining_seats INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_train (departure_time, train_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
              COLLATE=utf8mb4_unicode_ci
        """,
    },
}


def find_csv(data_dir: Path, pattern: str) -> Path:
    matches = sorted(data_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No CSV matching {pattern!r} was found in {data_dir}"
        )
    return matches[-1]


def read_rows(path: Path, columns: list[str]) -> list[tuple[Any, ...]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = set(reader.fieldnames or [])
        missing_headers = [column for column in columns if column not in headers]
        if missing_headers:
            raise ValueError(
                f"{path.name} is missing columns: {missing_headers}"
            )

        return [
            tuple(
                value if (value := (row.get(column) or "").strip()) else None
                for column in columns
            )
            for row in reader
        ]


def build_upsert_sql(table: str, columns: list[str]) -> str:
    column_sql = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    update_sql = ", ".join(
        f"`{column}` = VALUES(`{column}`)" for column in columns
    )
    return (
        f"INSERT INTO `{table}` ({column_sql}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_sql}"
    )


def count_rows(cursor, table: str) -> int:
    cursor.execute(f"SELECT COUNT(*) AS row_count FROM `{table}`")
    return cursor.fetchone()["row_count"]


def import_csv_data(data_dir: Path) -> list[dict[str, Any]]:
    connection = get_connection()
    results = []

    try:
        with connection.cursor() as cursor:
            for table, config in TABLES.items():
                csv_path = find_csv(data_dir, config["file_pattern"])
                columns = config["columns"]
                rows = read_rows(csv_path, columns)

                cursor.execute(config["create_sql"])
                before_count = count_rows(cursor, table)

                if rows:
                    cursor.executemany(
                        build_upsert_sql(table, columns),
                        rows,
                    )

                after_count = count_rows(cursor, table)
                results.append(
                    {
                        "table": table,
                        "file": csv_path.name,
                        "csv_rows": len(rows),
                        "before": before_count,
                        "after": after_count,
                        "inserted": after_count - before_count,
                    }
                )

        connection.commit()
        return results
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import travel planner CSV files into MySQL."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing the CSV files.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    results = import_csv_data(data_dir)

    print(f"Imported CSV data from: {data_dir}")
    for result in results:
        print(
            "{table}: file={file}, csv_rows={csv_rows}, "
            "before={before}, after={after}, inserted={inserted}".format(
                **result
            )
        )


if __name__ == "__main__":
    main()
