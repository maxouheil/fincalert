import os
from pathlib import Path
import ee

from sentinel_processor import SentinelProcessor


def main():
    # Initialize EE using the same service account json in project root
    project_root = Path(__file__).parent.parent.parent
    key_file = project_root / 'gee-service-account.json'
    credentials = ee.ServiceAccountCredentials(email=None, key_file=str(key_file))
    ee.Initialize(credentials)

    processor = SentinelProcessor()

    # Build tiles and pick the first one
    tiles = processor.create_processing_grid()
    if not tiles:
        raise RuntimeError('No tiles generated')

    sample_tile = tiles[0]

    # Process tile for last 6 months and export to GeoTIFF in /data
    image = processor.process_tile(sample_tile)

    output_path = project_root / 'data' / 'sample_tile.tif'
    processor.export_tile_to_geotiff(image, sample_tile, str(output_path))
    print(f'Exported sample tile to {output_path}')


if __name__ == '__main__':
    main()

