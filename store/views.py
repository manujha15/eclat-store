from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import stripe
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import (
    Category, Product, ProductVariant, Cart, CartItem,
    Order, OrderItem, Review, Wishlist, Coupon,
)

# ---------- Helpers ----------

def _get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


# ---------- Storefront ----------

def home(request):
    categories = Category.objects.all()
    featured = Product.objects.filter(is_active=True)[:8]
    return render(request, 'store/home.html', {
        'categories': categories,
        'featured': featured,
        'hero_video': '/media/hero/hero.mp4',
    })


def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__icontains=q)
        )

    min_price = request.GET.get('min')
    max_price = request.GET.get('max')
    if min_price:
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('base_price')
    elif sort == 'price_desc':
        products = products.order_by('-base_price')
    elif sort == 'new':
        products = products.order_by('-created_at')

    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'q': q,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'sort': sort or '',
    })


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True)
    categories = Category.objects.all()

    min_price = request.GET.get('min')
    max_price = request.GET.get('max')
    if min_price:
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('base_price')
    elif sort == 'price_desc':
        products = products.order_by('-base_price')

    return render(request, 'store/product_list.html', {
        'category': category,
        'products': products,
        'categories': categories,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'sort': sort or '',
        'q': '',
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    reviews = product.reviews.all()
    categories = Category.objects.all()

    user_review = None
    in_wishlist = False
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related': related,
        'reviews': reviews,
        'user_review': user_review,
        'in_wishlist': in_wishlist,
        'categories': categories,
    })


# ---------- Cart ----------

def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if variant.stock <= 0:
        messages.error(request, 'Sorry, this item is out of stock.')
        return redirect('store:product_detail', slug=variant.product.slug)

    cart = _get_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    if not created:
        if item.quantity + 1 > variant.stock:
            messages.warning(request, f'Only {variant.stock} left in stock.')
            return redirect('store:cart')
        item.quantity += 1
        item.save()
    messages.success(request, f'{variant.product.name} added to cart.')
    return redirect('store:cart')


def cart_view(request):
    cart = _get_cart(request)
    categories = Category.objects.all()
    return render(request, 'store/cart.html', {'cart': cart, 'categories': categories})


def remove_from_cart(request, item_id):
    cart = _get_cart(request)
    CartItem.objects.filter(id=item_id, cart=cart).delete()
    return redirect('store:cart')


# ---------- Auth ----------

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f'Welcome, {username}!')
            return redirect('store:home')

    return render(request, 'store/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('store:home')
        messages.error(request, 'Invalid credentials.')

    return render(request, 'store/login.html')


def logout_view(request):
    logout(request)
    return redirect('store:home')


# ---------- Checkout ----------

@login_required
def checkout(request):
    cart = _get_cart(request)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')

    if request.method == 'POST':
        # Coupon
        coupon = None
        discount = 0
        coupon_code = request.POST.get('coupon_code', '').strip()
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    code__iexact=coupon_code,
                    active=True,
                    valid_from__lte=timezone.now(),
                    valid_to__gte=timezone.now(),
                )
                if cart.total() < coupon.min_order_amount:
                    messages.error(
                        request,
                        f'Coupon requires minimum order of ₹{coupon.min_order_amount}.'
                    )
                    coupon = None
                else:
                    discount = round(cart.total() * coupon.discount_percent / 100, 2)
            except Coupon.DoesNotExist:
                messages.error(request, 'Invalid or expired coupon code.')
                coupon = None

        # Stock check
        for item in cart.items.all():
            if item.quantity > item.variant.stock:
                messages.error(
                    request,
                    f'Sorry, only {item.variant.stock} left of '
                    f'{item.variant.product.name} ({item.variant.size}).'
                )
                return redirect('store:cart')

        final_total = cart.total() - discount

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                full_name=request.POST['full_name'],
                email=request.POST['email'],
                phone=request.POST['phone'],
                address=request.POST['address'],
                city=request.POST['city'],
                state=request.POST['state'],
                pincode=request.POST['pincode'],
                total_amount=final_total,
                coupon=coupon,
                discount_amount=discount,
            )
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    size=item.variant.size,
                    color=item.variant.color,
                    price=item.variant.get_price(),
                    quantity=item.quantity,
                )
                v = item.variant
                v.stock = max(0, v.stock - item.quantity)
                v.save()

            cart.items.all().delete()

        # Confirmation email (prints to console in dev)
        try:
            items_text = '\n'.join(
                f'  {i.quantity} x {i.product_name} ({i.size}, {i.color}) - ₹{i.price}'
                for i in order.items.all()
            )
            body = (
                f'Hi {order.full_name},\n\n'
                f'Thanks for your order #{order.id}.\n\n'
                f'{items_text}\n\n'
                f'Total: ₹{order.total_amount}\n'
                f'Ship to: {order.address}, {order.city}, {order.state} - {order.pincode}\n\n'
                f'We will notify you when it ships.\n\n'
                f'— ÉCLAT'
            )
            send_mail(
                subject=f'Order #{order.id} confirmed',
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request, 'Order placed successfully!')
        return redirect('store:order_success', order_id=order.id)

    return render(request, 'store/checkout.html', {'cart': cart})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/my_orders.html', {
        'orders': orders,
        'categories': Category.objects.all(),
    })


# ---------- Reviews ----------

@login_required
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
            messages.error(request, 'Please select a rating between 1 and 5.')
            return redirect('store:product_detail', slug=slug)

        Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'rating': int(rating), 'comment': comment},
        )
        messages.success(request, 'Review saved.')
    return redirect('store:product_detail', slug=slug)


# ---------- Wishlist ----------

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item = Wishlist.objects.filter(user=request.user, product=product)
    if item.exists():
        item.delete()
        messages.success(request, f'Removed "{product.name}" from wishlist.')
    else:
        Wishlist.objects.create(user=request.user, product=product)
        messages.success(request, f'Added "{product.name}" to wishlist.')
    return redirect(request.META.get('HTTP_REFERER', 'store:product_list'))


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'store/wishlist.html', {
        'items': items,
        'categories': Category.objects.all(),
    })
# ---------- Stripe Payment ----------

@login_required
def stripe_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'PAID':
        messages.info(request, 'This order is already paid.')
        return redirect('store:order_success', order_id=order.id)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    success_url = request.build_absolute_uri(
        reverse('store:payment_success', args=[order.id])
    )
    cancel_url = request.build_absolute_uri(
        reverse('store:order_success', args=[order.id])
    )

    line_items = [{
        'price_data': {
            'currency': 'inr',
            'product_data': {'name': f'Order #{order.id} — ÉCLAT'},
            'unit_amount': int(order.total_amount * 100),
        },
        'quantity': 1,
    }]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            customer_email=order.email,
        )
        return redirect(session.url, permanent=False)
    except Exception as e:
        messages.error(request, f'Payment error: {e}')
        return redirect('store:order_success', order_id=order.id)


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'PAID'
    order.save()
    messages.success(request, 'Payment received. Thank you!')
    return render(request, 'store/payment_success.html', {'order': order})

# ---------- Buy Now & Quantity ----------

def buy_now(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if variant.stock <= 0:
        messages.error(request, 'Out of stock.')
        return redirect('store:product_detail', slug=variant.product.slug)

    cart = _get_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    if not created:
        item.quantity += 1
        item.save()

    if request.user.is_authenticated:
        return redirect('store:checkout')
    messages.info(request, 'Please log in to continue.')
    return redirect('store:login')


def increase_quantity(request, item_id):
    cart = _get_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    if item.quantity + 1 <= item.variant.stock:
        item.quantity += 1
        item.save()
    else:
        messages.warning(request, f'Only {item.variant.stock} in stock.')
    return redirect('store:cart')


def decrease_quantity(request, item_id):
    cart = _get_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
    return redirect('store:cart')

def home(request):
    categories = Category.objects.all()
    featured = Product.objects.filter(is_active=True)[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:12]
    return render(request, 'store/home.html', {
        'categories': categories,
        'featured': featured,
        'new_arrivals': new_arrivals,
        'hero_video': '/media/hero/hero.mp4',
    })  

from django.http import JsonResponse

def search_api(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        Q(name__icontains=q) |
        Q(brand__icontains=q) |
        Q(description__icontains=q),
        is_active=True,
    )[:8]

    results = []
    for p in products:
        results.append({
            'name': p.name,
            'brand': p.brand,
            'price': str(p.base_price),
            'url': reverse('store:product_detail', args=[p.slug]),
            'image': p.image.url if p.image else '',
        })

    return JsonResponse({'results': results})