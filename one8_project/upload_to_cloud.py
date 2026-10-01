import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'one8_project.settings')
django.setup()

import cloudinary
import cloudinary.uploader
from pathlib import Path
from django.conf import settings
from store.models import Product

cloudinary.config(
    cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
    api_secret=settings.CLOUDINARY_STORAGE['API_SECRET'],
)

media_dir = Path('media/products')
uploaded = 0
skipped = 0
errors = 0

print(f"Cloudinary cloud: {settings.CLOUDINARY_STORAGE['CLOUD_NAME']}")
print(f"Media dir: {media_dir.absolute()}\n")

for product in Product.objects.all():
    if not product.image:
        print(f"SKIP (no image field): {product.name}")
        skipped += 1
        continue

    file_name = Path(product.image.name).name
    file_path = media_dir / file_name

    if not file_path.exists():
        print(f"SKIP (file missing): {product.name} → {file_path}")
        skipped += 1
        continue

    try:
        print(f"Uploading {file_name} for {product.name}...")
        result = cloudinary.uploader.upload(
            str(file_path),
            folder='products',
            public_id=Path(file_name).stem,
            overwrite=True,
        )
        # Save public_id so Cloudinary resolves it
        product.image.name = f"products/{Path(file_name).stem}"
        product.save()
        print(f"  ✓ {result['secure_url']}")
        uploaded += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        errors += 1

# Hero video
video_path = Path('media/hero/hero.mp4')
if video_path.exists():
    print(f"\nUploading hero video...")
    try:
        result = cloudinary.uploader.upload(
            str(video_path),
            resource_type='video',
            folder='hero',
            public_id='hero',
            overwrite=True,
        )
        print(f"  ✓ VIDEO URL: {result['secure_url']}")
    except Exception as e:
        print(f"  ✗ Video error: {e}")
else:
    print(f"\nSKIP: Video not found at {video_path}")

print(f"\n===== DONE =====")
print(f"Uploaded: {uploaded}")
print(f"Skipped:  {skipped}")
print(f"Errors:   {errors}")