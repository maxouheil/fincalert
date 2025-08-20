#!/usr/bin/env python3
"""
Optimize DOTA dataset for 6-hour training by selecting best images.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def select_best_images(dataset_path: Path, target_train: int = 1000, target_val: int = 300) -> Dict:
    """Select best images with most vehicles for training"""
    
    print(f"🎯 Selecting best images for 6-hour training...")
    print(f"  Target: {target_train} train, {target_val} val images")
    
    selected = {'train': [], 'val': []}
    
    for split in ['train', 'val']:
        labels_dir = dataset_path / split / 'labels'
        images_dir = dataset_path / split / 'images'
        
        if not labels_dir.exists():
            continue
        
        # Get all label files (images with vehicles)
        label_files = list(labels_dir.glob('*.txt'))
        
        # Count vehicles in each image
        image_vehicle_counts = []
        for label_file in label_files:
            with open(label_file, 'r') as f:
                lines = f.readlines()
                vehicle_count = len([line for line in lines if line.strip()])
                image_name = label_file.stem
                image_path = images_dir / f"{image_name}.png"
                if image_path.exists():
                    image_vehicle_counts.append((image_path, label_file, vehicle_count))
        
        # Sort by vehicle count (descending) - prioritize images with more vehicles
        image_vehicle_counts.sort(key=lambda x: x[2], reverse=True)
        
        # Select target number of images
        target = target_train if split == 'train' else target_val
        selected_images = image_vehicle_counts[:target]
        
        selected[split] = selected_images
        
        print(f"  {split}: Selected {len(selected_images)} images")
        if selected_images:
            avg_vehicles = np.mean([img[2] for img in selected_images])
            total_vehicles = sum([img[2] for img in selected_images])
            print(f"    Average vehicles per image: {avg_vehicles:.1f}")
            print(f"    Total vehicles: {total_vehicles}")
    
    return selected


def create_optimized_dataset(source_path: Path, selected_images: Dict, output_path: Path) -> None:
    """Create optimized dataset with selected images"""
    
    print(f"\n📁 Creating optimized dataset...")
    
    # Create output structure
    for split in ['train', 'val']:
        (output_path / split / 'images').mkdir(parents=True, exist_ok=True)
        (output_path / split / 'labels').mkdir(parents=True, exist_ok=True)
    
    total_vehicles = 0
    
    for split, images in selected_images.items():
        print(f"  Processing {split}...")
        
        for i, (image_path, label_path, vehicle_count) in enumerate(images):
            # Copy image
            dest_image = output_path / split / 'images' / f"dota_{split}_{i:04d}.png"
            shutil.copy2(image_path, dest_image)
            
            # Copy label
            dest_label = output_path / split / 'labels' / f"dota_{split}_{i:04d}.txt"
            shutil.copy2(label_path, dest_label)
            
            total_vehicles += vehicle_count
        
        print(f"    Copied {len(images)} images")
    
    # Create data.yaml
    data_yaml = {
        'path': str(output_path),
        'train': 'train/images',
        'val': 'val/images',
        'test': 'test/images',
        'names': {0: 'car', 1: 'truck'},
        'nc': 2
    }
    
    yaml_path = output_path / 'data.yaml'
    with open(yaml_path, 'w') as f:
        import yaml
        yaml.dump(data_yaml, f, default_flow_style=False)
    
    print(f"  ✅ Optimized dataset created")
    print(f"  📊 Total vehicles: {total_vehicles}")
    print(f"  📁 Output: {output_path}")


def estimate_training_time(total_images: int) -> str:
    """Estimate training time based on dataset size"""
    
    # Rough estimation based on YOLOv8s on Apple MPS
    # ~2-3 seconds per epoch per 1000 images
    epochs = 25
    time_per_epoch = total_images / 1000 * 2.5  # seconds
    total_time_seconds = time_per_epoch * epochs
    total_time_hours = total_time_seconds / 3600
    
    return f"{total_time_hours:.1f}h"


def main():
    """Main optimization function"""
    
    # Paths
    source_path = ROOT / 'data' / 'datasets' / 'dota_yolo_vehicles'
    output_path = ROOT / 'data' / 'datasets' / 'dota_yolo_vehicles_6h'
    
    if not source_path.exists():
        print(f"❌ Source dataset not found at: {source_path}")
        return 1
    
    print("🚀 DOTA Dataset Optimization for 6-Hour Training")
    print("=" * 60)
    
    # Select best images
    selected = select_best_images(source_path, target_train=1000, target_val=300)
    
    # Create optimized dataset
    create_optimized_dataset(source_path, selected, output_path)
    
    # Calculate totals
    total_images = sum(len(images) for images in selected.values())
    total_vehicles = sum(sum(img[2] for img in images) for images in selected.values())
    training_time = estimate_training_time(total_images)
    
    print(f"\n" + "=" * 60)
    print("📋 Optimization Summary:")
    print(f"  Train images: {len(selected['train'])}")
    print(f"  Val images: {len(selected['val'])}")
    print(f"  Total images: {total_images}")
    print(f"  Total vehicles: {total_vehicles}")
    print(f"  Estimated training time: {training_time}")
    
    print(f"\n🎯 Ready for 6-hour training!")
    print(f"  Dataset: {output_path}")
    print(f"  Next: Run train_dota_vehicles.py")
    
    return 0


if __name__ == "__main__":
    exit(main())
