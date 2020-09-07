# hash_image_files



Installation:
pip install requirements.txt

Usage:
python get_image_uuids.py --rt <directory containing image files> --dst <output filename>.csv
  
Example:
python get_image_uuids.py --rt /home/Ben/Pictures/  --dst image_uuids.csv

This will grab all image files in /home/Ben/Pictures/ and sub-directories. The image files are hashed to generate deterministic uuids. Results are saved to image_uuids.csv

Resulting csv file has one row per image file. The first column is the image file path, the second contains the generated uuid and the last column contains the image file type

