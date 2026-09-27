from django.contrib import admin
from .models import (
    Category, Product, ProductVariant, ProductMedia,
    Cart, CartItem, Order, OrderItem, Review, Wishlist, Coupon,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'stock', 'price', 'sku')


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ('media_type', 'file', 'caption', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'base_price', 'is_active')
    list_filter = ('category', 'brand', 'is_active')
    search_fields = ('name', 'brand', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline, ProductMediaInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_percent', 'min_order_amount',
        'valid_from', 'valid_to', 'active',
    )
    list_filter = ('active',)
    search_fields = ('code',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'full_name', 'total_amount',
        'discount_amount', 'coupon', 'status', 'created_at',
    )
    list_filter = ('status', 'created_at', 'coupon')
    list_editable = ('status',)
    search_fields = ('full_name', 'email', 'phone')
    readonly_fields = ('created_at',)
    actions = ['mark_paid', 'mark_shipped', 'mark_delivered', 'mark_cancelled']

    @admin.action(description='Mark selected orders as PAID')
    def mark_paid(self, request, queryset):
        queryset.update(status='PAID')

    @admin.action(description='Mark selected orders as SHIPPED')
    def mark_shipped(self, request, queryset):
        queryset.update(status='SHIPPED')

    @admin.action(description='Mark selected orders as DELIVERED')
    def mark_delivered(self, request, queryset):
        queryset.update(status='DELIVERED')

    @admin.action(description='Mark selected orders as CANCELLED')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(OrderItem)