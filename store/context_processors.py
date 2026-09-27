from .models import Cart


def cart_count(request):
    count = 0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            key = request.session.session_key
            cart = Cart.objects.filter(session_key=key).first() if key else None
        if cart:
            count = sum(i.quantity for i in cart.items.all())
    except Exception:
        pass
    return {'cart_count': count}