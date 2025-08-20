#!/usr/bin/env python3
"""Train YOLOv8 vehicles with optional torchvision stub to bypass _lzma issues."""

# --- Torchvision stub to avoid _lzma import issues on systems without lzma ---
try:
    import torchvision  # noqa: F401
except Exception:  # pragma: no cover
    import sys as _sys, types as _types
    try:
        import torch as _torch  # type: ignore
    except Exception:  # pragma: no cover
        _torch = None
    tv = _types.ModuleType('torchvision')
    ops = _types.ModuleType('torchvision.ops')
    def _nms(boxes, scores, iou_thres: float):
        if _torch is None or boxes is None or scores is None:
            return []
        if boxes.numel() == 0:
            return _torch.empty((0,), dtype=_torch.long)
        x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
        areas = (x2 - x1).clamp(min=0) * (y2 - y1).clamp(min=0)
        order = scores.argsort(descending=True)
        keep = []
        while order.numel() > 0:
            i = int(order[0])
            keep.append(i)
            if order.numel() == 1:
                break
            xx1 = _torch.maximum(x1[i], x1[order[1:]])
            yy1 = _torch.maximum(y1[i], y1[order[1:]])
            xx2 = _torch.minimum(x2[i], x2[order[1:]])
            yy2 = _torch.minimum(y2[i], y2[order[1:]])
            w = (xx2 - xx1).clamp(min=0)
            h = (yy2 - yy1).clamp(min=0)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            inds = (iou <= iou_thres).nonzero(as_tuple=False).squeeze(1)
            order = order[inds + 1]
        return _torch.tensor(keep, dtype=_torch.long)
    ops.nms = _nms
    tv.ops = ops
    _sys.modules['torchvision'] = tv
    _sys.modules['torchvision.ops'] = ops
    for name in ['datasets','io','models','transforms','utils','_meta_registrations']:
        _sys.modules[f'torchvision.{name}'] = _types.ModuleType(f'torchvision.{name}')
"""
Fine-tune YOLOv8 on a vehicle dataset (Roboflow export or local tiles).

Examples:
  # Train on Roboflow dataset after download
  python scripts/train_vehicles_yolov8.py \
    --data data/vehicles_roboflow/data.yaml \
    --model yolov8s.pt --epochs 80 --img 640 --name yolov8_vehicles_rf

  # Train on locally prepared tiles
  python scripts/train_vehicles_yolov8.py \
    --data data/vehicles/dataset.yaml \
    --model yolov8n.pt --epochs 60 --img 640 --name yolov8_vehicles_local
"""

from pathlib import Path
import argparse

try:
    from ultralytics import YOLO
except Exception as e:  # pragma: no cover
    raise SystemExit("Ultralytics not installed. pip install ultralytics")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='dataset YAML path')
    parser.add_argument('--model', default='yolov8n.pt', help='base weights (yolov8n.pt/yolov8s.pt)')
    parser.add_argument('--epochs', type=int, default=60)
    parser.add_argument('--img', type=int, default=640)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--device', default=None, help='compute device (e.g., cpu, mps, 0)')
    parser.add_argument('--name', default='yolov8_vehicles')
    args = parser.parse_args()

    out_project = Path('data/vehicles/runs').resolve()
    out_project.mkdir(parents=True, exist_ok=True)

    model = YOLO(args.model)
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.img,
        batch=args.batch,
        name=args.name,
        project=str(out_project),
        patience=25,
        cos_lr=True,
        workers=args.workers,
        device=args.device if args.device else None,
    )
    print(results)
    print('\nTraining complete. Best weights should be under:')
    print(out_project / args.name / 'weights' / 'best.pt')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


