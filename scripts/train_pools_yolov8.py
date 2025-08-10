#!/usr/bin/env python3
"""
Train a YOLOv8 model for swimming pool detection using Roboflow dataset.

Requires:
  - ROBOFLOW_API_KEY in environment
  - Project: hiro-pwysl/swimming-pool-8tokb (expects a version v1+)

It downloads dataset in YOLOv8 format, runs a short training, and saves weights to
backend/yolo_pools.pt for inference in YOLOPoolDetector.
"""

from __future__ import annotations

import os
from pathlib import Path

from ultralytics import YOLO

try:
    from roboflow import Roboflow
except Exception as e:
    raise SystemExit("Roboflow SDK is required. pip install roboflow")


def main() -> int:
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        print("ERROR: ROBOFLOW_API_KEY not set")
        return 1

    rf = Roboflow(api_key=api_key)
    ws = rf.workspace("hiro-pwysl")
    proj = ws.project("swimming-pool-8tokb")

    # Prefer v1; adjust if you create newer versions
    version = proj.version(1)
    dataset = version.download("yolov8")
    data_yaml = Path(dataset.location) / "data.yaml"

    # Train a lightweight model (adjust epochs if you want better accuracy)
    model = YOLO("yolov8n.pt")
    model.train(data=str(data_yaml), imgsz=640, epochs=12, batch=-1, device=0 if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu")

    # Save best weights to backend/yolo_pools.pt
    run_dir = Path(model.trainer.save_dir)
    best = run_dir / "weights" / "best.pt"
    out = Path(__file__).resolve().parents[1] / "backend" / "yolo_pools.pt"
    out.write_bytes(best.read_bytes())
    print(f"Saved weights to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


