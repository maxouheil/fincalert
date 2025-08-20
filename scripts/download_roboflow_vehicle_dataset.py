#!/usr/bin/env python3
"""
Download the Roboflow 'Car Aerial View' dataset in YOLOv8 format for training.

Reference: https://universe.roboflow.com/tugas-akhir-hov0z/car-aerial-view

Requirements:
  pip install roboflow

Usage:
  export ROBOFLOW_API_KEY=...  # required
  python scripts/download_roboflow_vehicle_dataset.py \
    --workspace tugas-akhir-hov0z \
    --project car-aerial-view \
    --version 1 \
    --out data/vehicles_roboflow

This will download the dataset and print the path to dataset.yaml.
"""

import os
import sys
import shutil
from pathlib import Path
import argparse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', default='tugas-akhir-hov0z')
    parser.add_argument('--project', default='car-aerial-view')
    parser.add_argument('--version', type=int, default=1)
    parser.add_argument('--format', default='yolov8')
    parser.add_argument('--out', default='data/vehicles_roboflow')
    args = parser.parse_args()

    api_key = os.getenv('ROBOFLOW_API_KEY')
    if not api_key:
        print('ERROR: ROBOFLOW_API_KEY is not set', file=sys.stderr)
        return 2

    try:
        from roboflow import Roboflow  # type: ignore
    except Exception as e:
        print('Missing dependency. Please install with: pip install roboflow', file=sys.stderr)
        return 2

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Roboflow dataset: {args.workspace}/{args.project} v{args.version} → {out_dir}")
    rf = Roboflow(api_key=api_key)
    ws = rf.workspace(args.workspace)
    proj = ws.project(args.project)
    ver = proj.version(args.version)
    ds = ver.download(args.format)

    # Roboflow creates a folder like {ProjectName}-{version}/; move under out_dir
    src_dir = Path(ds.location).resolve()
    # Expect dataset.yaml at src_dir/data.yaml or dataset.yaml depending on format
    # YOLOv8 export typically includes data.yaml
    yaml_path = src_dir / 'data.yaml'
    if not yaml_path.exists():
        # fallback name
        yaml_path = src_dir / 'dataset.yaml'

    # Move/merge into out_dir
    for item in src_dir.iterdir():
        dest = out_dir / item.name
        if item.is_dir():
            if dest.exists():
                # Merge directories (simple copy)
                for sub in item.rglob('*'):
                    rel = sub.relative_to(item)
                    d = dest / rel
                    if sub.is_dir():
                        d.mkdir(parents=True, exist_ok=True)
                    else:
                        d.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sub, d)
            else:
                shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    print('Download complete.')
    final_yaml = out_dir / (yaml_path.name)
    if final_yaml.exists():
        print(f"Dataset YAML: {final_yaml}")
    else:
        print('WARNING: dataset YAML not found; please locate it under the downloaded folder.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())


