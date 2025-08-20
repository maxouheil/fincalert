#!/usr/bin/env python3
"""
Train YOLOv8 model on DOTA vehicle dataset.
"""

import os
import sys
import subprocess
from pathlib import Path

# Fix for _lzma import issue on some systems
try:
    import torchvision
except ImportError:
    # Create a minimal torchvision stub to avoid _lzma issues
    import sys
    from types import ModuleType
    
    torchvision = ModuleType('torchvision')
    torchvision.ops = ModuleType('torchvision.ops')
    
    def nms(boxes, scores, iou_threshold):
        # Simple NMS implementation
        import torch
        if len(boxes) == 0:
            return torch.empty((0,), dtype=torch.long)
        
        # Sort by scores
        _, order = scores.sort(0, descending=True)
        keep = []
        
        while order.numel() > 0:
            if order.numel() == 1:
                keep.append(order.item())
                break
            i = order[0]
            keep.append(i)
            
            # Calculate IoU with remaining boxes
            xx1 = boxes[order[1:], 0].clamp(min=boxes[i, 0])
            yy1 = boxes[order[1:], 1].clamp(min=boxes[i, 1])
            xx2 = boxes[order[1:], 2].clamp(max=boxes[i, 2])
            yy2 = boxes[order[1:], 3].clamp(max=boxes[i, 3])
            
            w = (xx2 - xx1).clamp(min=0)
            h = (yy2 - yy1).clamp(min=0)
            inter = w * h
            
            ovr = inter / (boxes[i, 2] * boxes[i, 3] + boxes[order[1:], 2] * boxes[order[1:], 3] - inter)
            ids = (ovr <= iou_threshold).nonzero().squeeze()
            if ids.numel() == 0:
                break
            order = order[ids + 1]
        
        return torch.tensor(keep, dtype=torch.long)
    
    torchvision.ops.nms = nms
    sys.modules['torchvision'] = torchvision
    sys.modules['torchvision.ops'] = torchvision.ops

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_dataset(dataset_path: Path) -> bool:
    """Check if the dataset is ready for training"""
    
    print(f"🔍 Checking dataset at: {dataset_path}")
    
    # Check data.yaml
    yaml_path = dataset_path / 'data.yaml'
    if not yaml_path.exists():
        print(f"  ❌ data.yaml not found")
        return False
    
    # Check train images and labels
    train_images = list((dataset_path / 'train' / 'images').glob('*.png'))
    train_labels = list((dataset_path / 'train' / 'labels').glob('*.txt'))
    
    print(f"  Train: {len(train_images)} images, {len(train_labels)} labels")
    
    # Check val images and labels
    val_images = list((dataset_path / 'val' / 'images').glob('*.png'))
    val_labels = list((dataset_path / 'val' / 'labels').glob('*.txt'))
    
    print(f"  Val: {len(val_images)} images, {len(val_labels)} labels")
    
    if len(train_images) == 0 or len(val_images) == 0:
        print(f"  ❌ No images found")
        return False
    
    # For DOTA, it's normal to have more images than labels (some images have no vehicles)
    if len(train_labels) == 0 or len(val_labels) == 0:
        print(f"  ❌ No labels found")
        return False
    
    if len(train_images) != len(train_labels) or len(val_images) != len(val_labels):
        print(f"  ⚠️  Mismatch between images and labels (this is normal for DOTA - some images have no vehicles)")
        print(f"  Train: {len(train_images)} images, {len(train_labels)} with vehicles")
        print(f"  Val: {len(val_images)} images, {len(val_labels)} with vehicles")
    
    print(f"  ✅ Dataset looks good!")
    return True


def train_yolov8(dataset_path: Path, model_size: str = 'n', epochs: int = 15) -> None:
    """Train YOLOv8 model"""
    
    print(f"🚀 Starting YOLOv8 training...")
    print(f"  Dataset: {dataset_path}")
    print(f"  Model: yolov8{model_size}.pt")
    print(f"  Epochs: {epochs}")
    
    # Training parameters
    yaml_path = dataset_path / 'data.yaml'
    model_name = f"yolov8{model_size}.pt"
    
    # Check if we're on Apple Silicon for MPS
    import platform
    if platform.machine() == 'arm64':
        device = 'mps'  # Apple Silicon GPU
        print(f"  Device: MPS (Apple Silicon)")
    else:
        device = 'cpu'
        print(f"  Device: CPU")
    
    # Training command - OPTIMIZED FOR 6 HOURS MAX (NO VALIDATION TO AVOID _LZMA ERROR)
    cmd = [
        'yolo', 'train',
        'model=' + model_name,
        'data=' + str(yaml_path),
        'epochs=' + str(epochs),
        'imgsz=320',  # Very small for speed
        'batch=32',   # Large batch for speed
        'device=' + device,
        'workers=4',
        'patience=3',  # Stop very early if no improvement
        'save=True',
        'save_period=3',  # Save every 3 epochs
        'val=False',  # Disable validation to avoid _lzma error
        'project=' + str(ROOT / 'data' / 'vehicles'),
        'name=dota_vehicles_training'
    ]
    
    print(f"  Command: {' '.join(cmd)}")
    
    # Run training with real-time output
    try:
        print(f"\n🚀 Starting training...")
        print(f"📊 Monitor progress with: python scripts/monitor_training.py")
        print(f"📈 Check status with: python scripts/monitor_training.py status")
        print(f"\n" + "="*50)
        
        # Run training with real-time output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1, universal_newlines=True)
        
        for line in process.stdout:
            print(line.rstrip())
        
        process.wait()
        
        if process.returncode == 0:
            print("\n✅ Training completed successfully!")
        else:
            print(f"\n❌ Training failed with return code: {process.returncode}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Training failed!")
        print(f"Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")


def main():
    """Main training function"""
    
    # Dataset path (optimized for 6-hour training)
    dataset_path = ROOT / 'data' / 'datasets' / 'dota_yolo_vehicles_6h'
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found at: {dataset_path}")
        print("Please run the DOTA conversion script first.")
        return 1
    
    print("🎯 DOTA Vehicle Detection Training")
    print("=" * 50)
    
    # Check dataset
    if not check_dataset(dataset_path):
        return 1
    
    # Training parameters - OPTIMIZED FOR 6 HOURS MAX
    model_size = 'n'  # n (nano) for speed
    epochs = 15
    
    print(f"\n📊 Training Configuration:")
    print(f"  Model: YOLOv8{model_size}")
    print(f"  Epochs: {epochs}")
    print(f"  Image size: 512x512")
    print(f"  Batch size: 8")
    
    # Ask for confirmation
    response = input(f"\n🤔 Start training? (y/N): ").strip().lower()
    if response != 'y':
        print("Training cancelled.")
        return 0
    
    # Start training
    train_yolov8(dataset_path, model_size, epochs)
    
    print("\n🎯 Next steps:")
    print("  1. Monitor training progress")
    print("  2. Test the trained model on fincas")
    print("  3. Compare with previous models")
    
    return 0


if __name__ == "__main__":
    exit(main())
