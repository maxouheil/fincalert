#!/usr/bin/env python3
"""
Compare overlay quality and analyze image resolution
"""

import os
import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

def analyze_image_quality(image_path: Path) -> dict:
    """Analyze image quality and resolution"""
    try:
        image = Image.open(image_path)
        
        # Basic info
        width, height = image.size
        format_type = image.format
        mode = image.mode
        
        # Convert to numpy for analysis
        img_array = np.array(image)
        
        # Calculate sharpness (Laplacian variance)
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2).astype(np.uint8)
        else:
            gray = img_array
            
        laplacian = np.var(cv2.Laplacian(gray, cv2.CV_64F))
        
        # Calculate contrast
        contrast = np.std(gray)
        
        # Calculate brightness
        brightness = np.mean(gray)
        
        return {
            'size': (width, height),
            'format': format_type,
            'mode': mode,
            'sharpness': laplacian,
            'contrast': contrast,
            'brightness': brightness,
            'file_size_mb': image_path.stat().st_size / (1024 * 1024)
        }
    except Exception as e:
        return {'error': str(e)}

def create_comparison_grid(image_paths: list, output_path: Path, title: str = "Image Comparison"):
    """Create a grid comparison of images"""
    if not image_paths:
        return
    
    # Load images
    images = []
    for path in image_paths:
        try:
            img = Image.open(path)
            # Resize to same size for comparison
            img = img.resize((400, 400), Image.Resampling.LANCZOS)
            images.append(img)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            continue
    
    if not images:
        return
    
    # Calculate grid dimensions
    n_images = len(images)
    cols = min(3, n_images)
    rows = (n_images + cols - 1) // cols
    
    # Create grid
    grid_width = cols * 400
    grid_height = rows * 450  # Extra space for labels
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    draw = ImageDraw.Draw(grid)
    
    # Try to load font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Add title
    title_bbox = draw.textbbox((0, 0), title, font=font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (grid_width - title_width) // 2
    draw.text((title_x, 10), title, fill='black', font=font)
    
    # Place images
    for i, img in enumerate(images):
        row = i // cols
        col = i % cols
        
        x = col * 400
        y = 50 + row * 450
        
        # Paste image
        grid.paste(img, (x, y))
        
        # Add label
        label = f"Image {i+1}"
        draw.text((x + 10, y + 410), label, fill='black', font=font)
    
    # Save grid
    grid.save(output_path)
    print(f"Comparison grid saved to: {output_path}")

def main():
    print("🔍 Analyzing Overlay Quality")
    print("=" * 50)
    
    # Paths to analyze
    tiling_dir = ROOT / 'data' / 'overlays' / 'tiling_test'
    
    if not tiling_dir.exists():
        print(f"❌ Tiling directory not found: {tiling_dir}")
        return
    
    # Find overlay images
    overlay_files = list(tiling_dir.glob("*_overlay.jpg"))
    
    if not overlay_files:
        print("❌ No overlay files found")
        return
    
    print(f"Found {len(overlay_files)} overlay files")
    
    # Analyze each overlay
    results = []
    for overlay_path in overlay_files:
        print(f"\nAnalyzing: {overlay_path.name}")
        
        # Analyze quality
        quality = analyze_image_quality(overlay_path)
        
        if 'error' not in quality:
            print(f"  Size: {quality['size']}")
            print(f"  Sharpness: {quality['sharpness']:.2f}")
            print(f"  Contrast: {quality['contrast']:.2f}")
            print(f"  Brightness: {quality['brightness']:.2f}")
            print(f"  File size: {quality['file_size_mb']:.2f} MB")
            
            results.append({
                'file': overlay_path.name,
                'quality': quality
            })
        else:
            print(f"  Error: {quality['error']}")
    
    # Create comparison grids
    print(f"\n📊 Creating comparison grids...")
    
    # Group by finca
    finca_groups = {}
    for result in results:
        finca_id = result['file'].split('_')[0]
        if finca_id not in finca_groups:
            finca_groups[finca_id] = []
        finca_groups[finca_id].append(result)
    
    # Create comparison for each finca
    for finca_id, group in finca_groups.items():
        print(f"\nCreating comparison for {finca_id}...")
        
        # Sort by type (original, tiling, combined)
        group.sort(key=lambda x: x['file'])
        
        # Get file paths
        file_paths = [tiling_dir / result['file'] for result in group]
        
        # Create comparison grid
        output_path = tiling_dir / f"{finca_id}_comparison.jpg"
        create_comparison_grid(
            file_paths, 
            output_path, 
            f"{finca_id} - Overlay Comparison"
        )
    
    # Save analysis results
    analysis_file = tiling_dir / 'quality_analysis.json'
    with open(analysis_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Quality analysis saved to: {analysis_file}")
    
    # Summary
    print(f"\n📈 Quality Summary")
    print("=" * 50)
    
    if results:
        sharpness_values = [r['quality']['sharpness'] for r in results if 'sharpness' in r['quality']]
        contrast_values = [r['quality']['contrast'] for r in results if 'contrast' in r['quality']]
        file_sizes = [r['quality']['file_size_mb'] for r in results if 'file_size_mb' in r['quality']]
        
        if sharpness_values:
            print(f"Average sharpness: {np.mean(sharpness_values):.2f}")
            print(f"Max sharpness: {np.max(sharpness_values):.2f}")
            print(f"Min sharpness: {np.min(sharpness_values):.2f}")
        
        if contrast_values:
            print(f"Average contrast: {np.mean(contrast_values):.2f}")
            print(f"Max contrast: {np.max(contrast_values):.2f}")
            print(f"Min contrast: {np.min(contrast_values):.2f}")
        
        if file_sizes:
            print(f"Average file size: {np.mean(file_sizes):.2f} MB")
            print(f"Total size: {np.sum(file_sizes):.2f} MB")

if __name__ == "__main__":
    import cv2
    main()
