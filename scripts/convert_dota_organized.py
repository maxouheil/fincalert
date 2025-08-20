#!/usr/bin/env python3
"""
Convert DOTA dataset to YOLO format using organized train/val annotation directories.
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


def find_matching_pairs(images_dir: Path, labels_dir: Path) -> List[Tuple[Path, Path]]:
    """Find matching image-label pairs"""
    
    pairs = []
    
    # Get all image files
    image_files = {f.stem: f for f in images_dir.glob('*.png')}
    label_files = {f.stem: f for f in labels_dir.glob('*.txt')}
    
    # Find matches
    for img_stem, img_path in image_files.items():
        if img_stem in label_files:
            pairs.append((img_path, label_files[img_stem]))
    
    print(f"  Found {len(pairs)} matching pairs out of {len(image_files)} images and {len(label_files)} labels")
    
    return pairs


def convert_dota_to_yolo(dota_annotation: Path, image_path: Path, output_label_path: Path) -> int:
    """Convert a single DOTA annotation file to YOLO format"""
    
    # DOTA class mapping to our vehicle classes
    DOTA_TO_YOLO_CLASSES = {
        'small-vehicle': 0,  # car
        'large-vehicle': 1,  # truck
    }
    
    # Vehicle classes we want to keep
    VEHICLE_CLASSES = ['small-vehicle', 'large-vehicle']
    
    def parse_dota_annotation(annotation_file: Path) -> List[Dict]:
        """Parse a DOTA annotation file and return list of objects"""
        
        objects = []
        
        with open(annotation_file, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('imagesource:') or line.startswith('gsd:'):
                continue
                
            # Parse: x1,y1,x2,y2,x3,y3,x4,y4,class,difficulty
            parts = line.split()
            if len(parts) >= 9:
                try:
                    # Extract coordinates (first 8 values)
                    coords = [float(x) for x in parts[:8]]
                    class_name = parts[8]
                    difficulty = int(parts[9]) if len(parts) > 9 else 0
                    
                    # Only keep vehicle classes
                    if class_name in VEHICLE_CLASSES:
                        objects.append({
                            'coords': coords,
                            'class': class_name,
                            'difficulty': difficulty
                        })
                except (ValueError, IndexError):
                    continue
        
        return objects
    
    def polygon_to_bbox(coords: List[float]) -> Tuple[float, float, float, float]:
        """Convert polygon coordinates to bounding box (x_center, y_center, width, height)"""
        
        # Extract x and y coordinates
        x_coords = coords[::2]  # x1, x2, x3, x4
        y_coords = coords[1::2]  # y1, y2, y3, y4
        
        # Calculate bounding box
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Calculate center and dimensions
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        width = x_max - x_min
        height = y_max - y_min
        
        return x_center, y_center, width, height
    
    def normalize_coordinates(x_center: float, y_center: float, width: float, height: float, 
                             img_width: int, img_height: int) -> Tuple[float, float, float, float]:
        """Normalize coordinates to [0,1] range for YOLO format"""
        
        x_norm = x_center / img_width
        y_norm = y_center / img_height
        w_norm = width / img_width
        h_norm = height / img_height
        
        return x_norm, y_norm, w_norm, h_norm
    
    # Parse DOTA annotation
    objects = parse_dota_annotation(dota_annotation)
    
    if not objects:
        return 0
    
    # Get image dimensions
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"⚠️  Could not read image: {image_path}")
        return 0
    
    img_height, img_width = img.shape[:2]
    
    # Convert objects to YOLO format
    yolo_lines = []
    
    for obj in objects:
        # Convert polygon to bbox
        x_center, y_center, width, height = polygon_to_bbox(obj['coords'])
        
        # Normalize coordinates
        x_norm, y_norm, w_norm, h_norm = normalize_coordinates(
            x_center, y_center, width, height, img_width, img_height
        )
        
        # Get YOLO class index
        dota_class = obj['class']
        if dota_class in DOTA_TO_YOLO_CLASSES:
            yolo_class = DOTA_TO_YOLO_CLASSES[dota_class]
            
            # YOLO format: class x_center y_center width height
            yolo_line = f"{yolo_class} {x_norm:.6f} {y_norm:.6f} {w_norm:.6f} {h_norm:.6f}"
            yolo_lines.append(yolo_line)
    
    # Write YOLO annotation file
    if yolo_lines:
        with open(output_label_path, 'w') as f:
            f.write('\n'.join(yolo_lines))
        return len(yolo_lines)
    
    return 0


def process_dota_split(dota_images_dir: Path, dota_labels_dir: Path, 
                      output_images_dir: Path, output_labels_dir: Path,
                      split_name: str) -> Dict:
    """Process a DOTA split with proper matching"""
    
    print(f"\n🔄 Processing {split_name} split...")
    
    # Find matching pairs
    pairs = find_matching_pairs(dota_images_dir, dota_labels_dir)
    
    if not pairs:
        print(f"  ❌ No matching pairs found for {split_name}")
        return {'total_images': 0, 'processed_images': 0, 'total_objects': 0}
    
    stats = {
        'total_images': len(pairs),
        'processed_images': 0,
        'total_objects': 0,
        'objects_by_class': {'car': 0, 'truck': 0}
    }
    
    for i, (image_path, annotation_path) in enumerate(pairs):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(pairs)}")
        
        # Copy image
        dest_image_path = output_images_dir / f"dota_{split_name}_{i:04d}.png"
        shutil.copy2(image_path, dest_image_path)
        
        # Convert annotation
        dest_label_path = output_labels_dir / f"dota_{split_name}_{i:04d}.txt"
        object_count = convert_dota_to_yolo(annotation_path, image_path, dest_label_path)
        
        if object_count > 0:
            stats['processed_images'] += 1
            stats['total_objects'] += object_count
            
            # Count by class (simplified)
            stats['objects_by_class']['car'] += object_count
    
    print(f"  ✅ Processed {stats['processed_images']}/{stats['total_images']} images")
    print(f"  📊 Total objects: {stats['total_objects']}")
    
    return stats


def add_finca_images(output_path: Path, sample_size: int = 30) -> None:
    """Add our finca images to the dataset"""
    
    print(f"\n🏠 Adding {sample_size} finca images...")
    
    # Load finca data from the correct location
    fincas_file = ROOT / 'frontend' / 'public' / 'data' / 'fincas.json'
    if not fincas_file.exists():
        # Try alternative location
        fincas_file = ROOT / 'data' / 'fincas.json'
        if not fincas_file.exists():
            print("  ⚠️  No fincas.json found")
            return
    
    with open(fincas_file, 'r') as f:
        fincas = json.load(f)
    
    # Take top fincas
    top_fincas = fincas[:sample_size]
    
    # Copy images and create empty labels (for now)
    for i, finca in enumerate(top_fincas):
        # Generate Mapbox URL
        lat, lon = finca['lat'], finca['lon']
        zoom = 21
        width, height = 1280, 1280
        
        # For now, create placeholder
        image_name = f"finca_{i:04d}.png"
        label_name = f"finca_{i:04d}.txt"
        
        # Create empty label file
        label_path = output_path / 'train' / 'labels' / label_name
        label_path.write_text("")  # Empty for now
        
        print(f"  Added: {image_name} (placeholder)")
    
    print(f"  ✅ Added {len(top_fincas)} finca placeholders")


def main():
    """Main conversion function"""
    
    # Paths
    dota_path = Path.home() / 'Downloads' / 'DOTA'
    dota_train_labels = Path.home() / 'Downloads' / 'labelTxt-v1.0 - train' / 'labelTxt'
    dota_val_labels = Path.home() / 'Downloads' / 'labelTxt-v1.0 -  val' / 'labelTxt'
    output_path = ROOT / 'data' / 'datasets' / 'dota_yolo_vehicles'
    
    if not dota_path.exists():
        print(f"❌ DOTA dataset not found at: {dota_path}")
        return 1
    
    if not dota_train_labels.exists():
        print(f"❌ DOTA train labels not found at: {dota_train_labels}")
        return 1
    
    if not dota_val_labels.exists():
        print(f"❌ DOTA val labels not found at: {dota_val_labels}")
        return 1
    
    print("🚀 Converting DOTA to YOLO Format (Organized)")
    print("=" * 50)
    
    # Create output structure
    for split in ['train', 'val', 'test']:
        (output_path / split / 'images').mkdir(parents=True, exist_ok=True)
        (output_path / split / 'labels').mkdir(parents=True, exist_ok=True)
    
    # Process each split
    total_stats = {}
    
    # Train split
    train_stats = process_dota_split(
        dota_path / 'train' / 'images',
        dota_train_labels,
        output_path / 'train' / 'images',
        output_path / 'train' / 'labels',
        'train'
    )
    total_stats['train'] = train_stats
    
    # Val split
    val_stats = process_dota_split(
        dota_path / 'val' / 'images',
        dota_val_labels,
        output_path / 'val' / 'images',
        output_path / 'val' / 'labels',
        'val'
    )
    total_stats['val'] = val_stats
    
    # Add finca images
    add_finca_images(output_path)
    
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
    
    print(f"  📄 Created data.yaml with 2 vehicle classes")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Conversion Summary:")
    for split, stats in total_stats.items():
        print(f"  {split}: {stats['processed_images']} images, {stats['total_objects']} objects")
    
    total_objects = sum(stats['total_objects'] for stats in total_stats.values())
    print(f"  Total objects: {total_objects}")
    print(f"  Output: {output_path}")
    
    print("\n🎯 Next steps:")
    print("  1. Review converted annotations")
    print("  2. Add real finca images with vehicle annotations")
    print("  3. Train YOLOv8 model")
    
    return 0


if __name__ == "__main__":
    exit(main())
