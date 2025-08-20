#!/usr/bin/env python3
"""
Download DOTA v2.0 dataset for vehicle detection training.

DOTA v2.0 is a large-scale dataset for object detection in aerial images.
Reference: https://captain-whu.github.io/DOTA/

This script downloads the dataset in parts and provides progress tracking.
"""

import os
import sys
import requests
import zipfile
from pathlib import Path
from tqdm import tqdm
import argparse


def download_file(url: str, dest_path: Path, chunk_size: int = 8192):
    """Download file with progress bar"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(dest_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=dest_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download DOTA v2.0 dataset")
    parser.add_argument('--out', default='data/datasets/dota', help='Output directory')
    parser.add_argument('--skip-download', action='store_true', help='Skip download, only convert')
    args = parser.parse_args()
    
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # DOTA v2.0 download URLs (these might need to be updated)
    dota_urls = {
        'train': 'https://captain-whu.github.io/DOTA/dataset_v2.0/train.tar.gz',
        'val': 'https://captain-whu.github.io/DOTA/dataset_v2.0/val.tar.gz',
        'test': 'https://captain-whu.github.io/DOTA/dataset_v2.0/test.tar.gz',
        'annotations': 'https://captain-whu.github.io/DOTA/dataset_v2.0/annotations.tar.gz'
    }
    
    if not args.skip_download:
        print("⚠️  DOTA v2.0 is a very large dataset (~15GB)")
        print("This will take a long time to download.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Download cancelled.")
            return 1
        
        print(f"Downloading DOTA v2.0 to {out_dir}")
        
        for split, url in dota_urls.items():
            dest_file = out_dir / f"{split}.tar.gz"
            print(f"\nDownloading {split}...")
            
            if download_file(url, dest_file):
                print(f"✅ {split} downloaded successfully")
            else:
                print(f"❌ Failed to download {split}")
                return 1
    
    # Alternative: Use a smaller, more accessible dataset
    print("\n🔍 DOTA v2.0 is very large and may be slow to download.")
    print("Alternative: Consider using a smaller dataset like:")
    print("  - VisDrone (10K images)")
    print("  - COWC (32K images)")
    print("  - Or continue with COCO model with better parameters")
    
    return 0


if __name__ == "__main__":
    exit(main())
