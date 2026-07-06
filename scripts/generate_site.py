#!/usr/bin/env python3
"""Generate the static wordspend site."""

import argparse
from pathlib import Path

from wordspend.site import generate_site


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", default="build/analysis")
    parser.add_argument("--catalog", default="data/work_catalog.csv")
    parser.add_argument("--output-dir", default="site")
    args = parser.parse_args()

    generate_site(
        analysis_dir=Path(args.analysis_dir),
        catalog_path=Path(args.catalog),
        output_dir=Path(args.output_dir),
    )
    print(f"Generated site in {args.output_dir}")


if __name__ == "__main__":
    main()
