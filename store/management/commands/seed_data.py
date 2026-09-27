from django.core.management.base import BaseCommand
from django.utils.text import slugify
from store.models import Category, Product, ProductVariant


CATEGORIES = [
    ('Skincare', 'Serums, moisturizers, and cleansers.'),
    ('Fragrance', 'Signature scents from rare botanicals.'),
    ('Makeup', 'Lips, eyes, and complexion.'),
    ('Body & Bath', 'Rituals for skin and senses.'),
    ('Hair', 'Nourishing care for healthy hair.'),
    ('Candles & Home', 'Ambient scents for the home.'),
]

PRODUCTS = [
    ('Skincare', 'Radiance Renewal Serum', 2499, 'img1.jpg',
     [('30ML', 'Clear', 40), ('50ML', 'Clear', 25)]),
    ('Skincare', 'Hydra Bloom Moisturizer', 1899, 'img2.jpg',
     [('50ML', 'Ivory', 30), ('100ML', 'Ivory', 15)]),
    ('Fragrance', 'Noir Botanique Parfum', 5499, 'img3.jpg',
     [('50ML', 'Amber', 20), ('100ML', 'Amber', 10)]),
    ('Fragrance', 'Citrus Bloom Cologne', 3999, 'img4.jpg',
     [('50ML', 'Clear', 35), ('100ML', 'Clear', 20)]),
    ('Makeup', 'Velvet Matte Lipstick', 1299, 'img5.jpg',
     [('SHADE-L', 'Rosewood', 25), ('SHADE-M', 'Terracotta', 30)]),
    ('Makeup', 'Luminous Silk Foundation', 2899, 'img1.jpg',
     [('SHADE-L', 'Ivory', 20), ('SHADE-M', 'Beige', 25)]),
    ('Body & Bath', 'Rose & Salt Body Polish', 1499, 'img2.jpg',
     [('ONE', 'Rose', 50)]),
    ('Hair', 'Silk Repair Hair Oil', 1799, 'img3.jpg',
     [('50ML', 'Gold', 30), ('100ML', 'Gold', 20)]),
    ('Candles & Home', 'Amber Noir Candle', 2199, 'img4.jpg',
     [('ONE', 'Amber', 40)]),
    ('Candles & Home', 'Fig & Cassis Diffuser', 2699, 'img5.jpg',
     [('ONE', 'Clear', 30)]),
]


class Command(BaseCommand):
    help = 'Seed demo data'

    def handle(self, *args, **opts):
        cats = {}
        for name, desc in CATEGORIES:
            c, _ = Category.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name), 'description': desc}
            )
            cats[name] = c
            self.stdout.write(f'Category: {c.name}')

        for cat_name, name, price, img, variants in PRODUCTS:
            p, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': cats[cat_name],
                    'brand': 'ECLAT',
                    'base_price': price,
                    'description': f'{name} - crafted for modern beauty rituals.',
                    'slug': slugify(name),
                    'image': f'products/{img}',
                    'is_active': True,
                }
            )
            self.stdout.write(f'Product: {p.name}')
            for size, color, stock in variants:
                sku = f'{slugify(name)[:10].upper()}-{size}-{color[:3].upper()}'
                ProductVariant.objects.get_or_create(
                    product=p, size=size, color=color,
                    defaults={'stock': stock, 'sku': sku}
                )

        self.stdout.write(self.style.SUCCESS('Done.'))