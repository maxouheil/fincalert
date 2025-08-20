#!/usr/bin/env python3
"""
Monitor YOLOv8 training progress in real-time.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def find_training_logs(project_path: Path) -> Path:
    """Find the latest training log file"""
    
    # Look for training runs
    runs_dir = project_path / 'dota_vehicles_training'
    if not runs_dir.exists():
        print(f"❌ No training runs found at: {runs_dir}")
        return None
    
    # Find the latest run
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not run_dirs:
        print(f"❌ No training runs found")
        return None
    
    latest_run = max(run_dirs, key=lambda x: x.stat().st_mtime)
    log_file = latest_run / 'results.csv'
    
    if not log_file.exists():
        print(f"❌ No results.csv found in {latest_run}")
        return None
    
    return log_file


def parse_training_log(log_file: Path) -> dict:
    """Parse the training log file"""
    
    if not log_file.exists():
        return None
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            return None
        
        # Parse header
        header = lines[0].strip().split(',')
        
        # Parse latest line
        latest_line = lines[-1].strip().split(',')
        
        # Create dict
        data = {}
        for i, key in enumerate(header):
            if i < len(latest_line):
                try:
                    data[key] = float(latest_line[i])
                except ValueError:
                    data[key] = latest_line[i]
        
        return data
    except Exception as e:
        print(f"Error parsing log: {e}")
        return None


def monitor_training(project_path: Path, check_interval: int = 30):
    """Monitor training progress"""
    
    print("🔍 Monitoring YOLOv8 Training Progress")
    print("=" * 50)
    
    start_time = datetime.now()
    last_epoch = 0
    
    while True:
        try:
            # Find log file
            log_file = find_training_logs(project_path)
            if not log_file:
                print("⏳ Waiting for training to start...")
                time.sleep(check_interval)
                continue
            
            # Parse current status
            data = parse_training_log(log_file)
            if not data:
                print("⏳ Waiting for training data...")
                time.sleep(check_interval)
                continue
            
            # Calculate progress
            current_epoch = int(data.get('epoch', 0))
            total_epochs = 25  # Our target
            
            if current_epoch > last_epoch:
                # New epoch started
                elapsed = datetime.now() - start_time
                progress = (current_epoch / total_epochs) * 100
                
                # Estimate remaining time
                if current_epoch > 0:
                    time_per_epoch = elapsed / current_epoch
                    remaining_epochs = total_epochs - current_epoch
                    eta = time_per_epoch * remaining_epochs
                    eta_str = str(timedelta(seconds=int(eta.total_seconds())))
                else:
                    eta_str = "Unknown"
                
                print(f"\n📊 Epoch {current_epoch}/{total_epochs} ({progress:.1f}%)")
                print(f"   ⏱️  Elapsed: {str(timedelta(seconds=int(elapsed.total_seconds())))}")
                print(f"   🎯 ETA: {eta_str}")
                
                # Show metrics if available
                if 'train/box_loss' in data:
                    print(f"   📈 Train Loss: {data['train/box_loss']:.4f}")
                if 'val/box_loss' in data:
                    print(f"   📉 Val Loss: {data['val/box_loss']:.4f}")
                if 'metrics/mAP50(B)' in data:
                    print(f"   🎯 mAP50: {data['metrics/mAP50(B)']:.4f}")
                
                last_epoch = current_epoch
                
                # Check if training is complete
                if current_epoch >= total_epochs:
                    print(f"\n🎉 Training completed!")
                    break
            
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error monitoring: {e}")
            time.sleep(check_interval)


def show_training_status(project_path: Path):
    """Show current training status"""
    
    print("📊 Current Training Status")
    print("=" * 30)
    
    log_file = find_training_logs(project_path)
    if not log_file:
        print("❌ No active training found")
        return
    
    data = parse_training_log(log_file)
    if not data:
        print("❌ No training data available")
        return
    
    current_epoch = int(data.get('epoch', 0))
    total_epochs = 25
    progress = (current_epoch / total_epochs) * 100
    
    print(f"Epoch: {current_epoch}/{total_epochs} ({progress:.1f}%)")
    
    if 'train/box_loss' in data:
        print(f"Train Loss: {data['train/box_loss']:.4f}")
    if 'val/box_loss' in data:
        print(f"Val Loss: {data['val/box_loss']:.4f}")
    if 'metrics/mAP50(B)' in data:
        print(f"mAP50: {data['metrics/mAP50(B)']:.4f}")


def main():
    """Main function"""
    
    project_path = ROOT / 'data' / 'vehicles'
    
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_training_status(project_path)
        return 0
    
    print("🚀 YOLOv8 Training Monitor")
    print("=" * 30)
    print("Press Ctrl+C to stop monitoring")
    print()
    
    monitor_training(project_path)
    
    return 0


if __name__ == "__main__":
    exit(main())
