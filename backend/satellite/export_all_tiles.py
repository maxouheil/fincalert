import argparse
import os
import time
from pathlib import Path
from typing import List, Dict

import ee

from sentinel_processor import SentinelProcessor


def export_tiles(max_tiles: int | None = None, delay_seconds: float = 2.0, bounds: dict | None = None) -> None:
    project_root = Path(__file__).parent.parent.parent

    # Initialize EE credentials using the service account
    key_file = project_root / 'gee-service-account.json'
    credentials = ee.ServiceAccountCredentials(email=None, key_file=str(key_file))
    ee.Initialize(credentials)

    processor = SentinelProcessor(bounds=bounds)

    tiles: List[Dict[str, float]] = processor.create_processing_grid()
    total = len(tiles)
    if max_tiles is not None:
        tiles = tiles[:max_tiles]
    
    output_dir = project_root / 'data' / 'tiles'
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting export of {len(tiles)}/{total} tiles to {output_dir} ...")

    successes = 0
    failures = 0

    for idx, tile in enumerate(tiles, start=1):
        fname = f"tile_{idx:03d}_{tile['west']:.4f}_{tile['south']:.4f}.tif"
        out_path = output_dir / fname

        if out_path.exists():
            print(f"[{idx}/{len(tiles)}] Exists, skipping: {out_path.name}")
            continue

        print(f"[{idx}/{len(tiles)}] Processing and exporting: {out_path.name}")

        # Process and export with retries
        tries = 0
        max_retries = 3
        while tries < max_retries:
            tries += 1
            try:
                image = processor.process_tile(tile)
                processor.export_tile_to_geotiff(image, tile, str(out_path))
                print(f"    ✓ Exported -> {out_path}")
                successes += 1
                break
            except Exception as e:
                print(f"    ✗ Attempt {tries}/{max_retries} failed: {e}")
                if tries >= max_retries:
                    failures += 1
                time.sleep(2.0 * tries)

        time.sleep(delay_seconds)

    print(f"Done. Successes: {successes}, Failures: {failures}, Output: {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export all 2x2 km tiles for Ibiza West")
    parser.add_argument("--max", type=int, default=None, help="Limit number of tiles to export")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between tile downloads (seconds)")
    parser.add_argument("--west", type=float, default=None, help="AOI west lon")
    parser.add_argument("--south", type=float, default=None, help="AOI south lat")
    parser.add_argument("--east", type=float, default=None, help="AOI east lon")
    parser.add_argument("--north", type=float, default=None, help="AOI north lat")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    bounds = None
    if all(v is not None for v in [args.west, args.south, args.east, args.north]):
        bounds = {"west": args.west, "south": args.south, "east": args.east, "north": args.north}
    export_tiles(max_tiles=args.max, delay_seconds=args.delay, bounds=bounds)

