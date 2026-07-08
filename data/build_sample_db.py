"""가상 건설 현장 데이터로 sample.db 를 생성한다. (모든 데이터는 가상)

    python data/build_sample_db.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "sample.db"

SCHEMA = """
CREATE TABLE sites (
    site_id    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    location   TEXT,
    start_date TEXT
);

CREATE TABLE floors (
    floor_id           INTEGER PRIMARY KEY,
    site_id            INTEGER NOT NULL,
    floor_name         TEXT,
    planned_elements   INTEGER,   -- 계획된 BIM 요소 수
    installed_elements INTEGER,   -- 실제 설치 판단된 요소 수
    FOREIGN KEY (site_id) REFERENCES sites(site_id)
);

CREATE VIEW progress AS
SELECT s.name                                              AS site_name,
       f.floor_name                                        AS floor_name,
       f.installed_elements                                AS installed,
       f.planned_elements                                  AS planned,
       ROUND(100.0 * f.installed_elements / f.planned_elements, 1) AS progress_pct
FROM floors f
JOIN sites s ON s.site_id = f.site_id;
"""

SITES = [
    (1, "강남 A현장", "서울 강남", "2025-03-01"),
    (2, "판교 B현장", "경기 성남", "2025-05-15"),
    (3, "송도 C현장", "인천 연수", "2025-01-10"),
]

# (floor_id, site_id, floor_name, planned, installed)
FLOORS = [
    (1, 1, "1층", 120, 120),
    (2, 1, "2층", 120, 110),
    (3, 1, "3층", 120, 72),
    (4, 2, "1층", 90, 90),
    (5, 2, "2층", 90, 45),
    (6, 3, "1층", 150, 150),
    (7, 3, "2층", 150, 140),
    (8, 3, "3층", 150, 138),
    (9, 3, "4층", 150, 60),
]


def main():
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    try:
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO sites VALUES (?,?,?,?)", SITES)
        con.executemany("INSERT INTO floors VALUES (?,?,?,?,?)", FLOORS)
        con.commit()

        print(f"생성 완료: {DB}")
        for row in con.execute(
            "SELECT site_name, floor_name, progress_pct FROM progress "
            "ORDER BY progress_pct LIMIT 3"
        ):
            print("  진척률 낮은 순:", row)
    finally:
        con.close()


if __name__ == "__main__":
    main()
