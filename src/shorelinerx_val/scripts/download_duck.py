#!/usr/bin/env python3
"""
Download FRF elevationTransects survey .nc files newer than a given date.

Usage:
    python3 download_frf_surveys.py --min-date 2024-02-01 --out ~/FRF_survey_data
    python3 download_frf_surveys.py --min-date 20240201            # also accepted
    python3 download_frf_surveys.py --min-date 2024-02-01 --dry-run
    python download_frf_surveys.py --min-date 2024-06-20 --out /home/florent/dev/SDS_Benchmark/datasets/DUCK/raw/ --dry-run
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

CATALOG_URL = (
    "https://chldata.erdc.dren.mil/thredds/catalog/frf/"
    "geomorphology/elevationTransects/survey/data/catalog.html"
)
BASE_URL = (
    "https://chldata.erdc.dren.mil/thredds/fileServer/frf/"
    "geomorphology/elevationTransects/survey/data"
)
FILENAME_RE = re.compile(
    r"FRF_geomorphology_elevationTransects_survey_(\d{8})\.nc"
)


def parse_date(s: str) -> datetime:
    s = s.replace("-", "")
    try:
        return datetime.strptime(s, "%Y%m%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{s}'. Use YYYY-MM-DD or YYYYMMDD."
        )


def get_filenames() -> list[str]:
    resp = requests.get(CATALOG_URL, timeout=300)
    resp.raise_for_status()
    names = sorted(set(FILENAME_RE.findall(resp.text)))
    return [f"FRF_geomorphology_elevationTransects_survey_{d}.nc" for d in names]


def download(fname: str, out_dir: Path, dry_run: bool) -> None:
    dest = out_dir / fname
    if dest.exists():
        print(f"skip (already have): {fname}")
        return
    if dry_run:
        print(f"[dry-run] would download: {fname}")
        return
    url = f"{BASE_URL}/{fname}"
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    print(f"downloaded: {fname}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--min-date",
        type=parse_date,
        required=True,
        help="Only download surveys on/after this date (YYYY-MM-DD or YYYYMMDD)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "FRF_survey_data",
        help="Output directory (default: ~/FRF_survey_data)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be downloaded without downloading",
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    print("Fetching catalog...")
    all_files = get_filenames()
    print(f"Found {len(all_files)} total files in catalog.")

    to_get = [
        f
        for f in all_files
        if datetime.strptime(FILENAME_RE.search(f).group(1), "%Y%m%d")
        >= args.min_date
    ]
    print(f"{len(to_get)} files match date >= {args.min_date:%Y-%m-%d}.")

    for fname in to_get:
        try:
            download(fname, args.out, args.dry_run)
        except requests.RequestException as e:
            print(f"ERROR downloading {fname}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()