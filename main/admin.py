from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Facility, PitchType, Pitch, Voucher,
    Booking, Review, Comment, Favorite
)

class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'full_name', 'phone_number', 'role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'full_name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân', {'fields': ('full_name', 'email', 'phone_number')}),
        ('Quyền hạn & Vai trò', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Kích hoạt tài khoản', {'fields': ('activation_token', 'activation_expiry')}),
        ('Ngày giờ', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )

class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'created_at', 'updated_at')
    search_fields = ('name', 'address')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

class PitchTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_per_page = 20

class PitchAdmin(admin.ModelAdmin):
    list_display = ('name', 'pitch_type', 'facility', 'base_price_per_hour', 'is_available', 'created_at')
    search_fields = ('name', 'address')
    list_filter = ('facility', 'pitch_type', 'is_available')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)
    raw_id_fields = ('pitch_type', 'facility')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pitch_type', 'facility')

class VoucherAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'min_order_value', 'usage_limit', 'used_count', 'is_active', 'start_date', 'end_date', 'created_at')
    search_fields = ('code', 'description')
    list_filter = ('is_active', 'start_date', 'end_date')
    readonly_fields = ('created_at', 'used_count')
    list_editable = ('is_active',)
    list_per_page = 20
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('code',)
        return self.readonly_fields

class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'pitch', 'user', 'booking_date', 'start_time', 'end_time', 'duration_hours', 'final_price', 'status')
    search_fields = ('pitch__name', 'user__username', 'user__full_name')
    list_filter = ('status', 'pitch__facility', 'booking_date')
    date_hierarchy = 'booking_date'
    readonly_fields = ('created_at', 'updated_at', 'duration_hours', 'final_price')
    raw_id_fields = ('user', 'pitch', 'voucher')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'pitch', 'voucher')
    
    def save_model(self, request, obj, form, change):
        """Auto-calculate duration and price when saving in admin"""
        if not change:  # Only for new bookings
            obj.full_clean()
        super().save_model(request, obj, form, change)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'pitch', 'rating', 'created_at', 'updated_at')
    search_fields = ('user__username', 'pitch__name', 'content')
    list_filter = ('rating', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'pitch')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'pitch')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'review', 'parent_comment', 'created_at', 'updated_at')
    search_fields = ('user__username', 'review__pitch__name', 'content')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'review', 'parent_comment')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'review')

class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'pitch', 'created_at')
    search_fields = ('user__username', 'pitch__name')
    list_filter = ('pitch__facility', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'pitch')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'pitch')

admin.site.register(User, CustomUserAdmin)
admin.site.register(Facility, FacilityAdmin)
admin.site.register(PitchType, PitchTypeAdmin)
admin.site.register(Pitch, PitchAdmin)
admin.site.register(Voucher, VoucherAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Favorite, FavoriteAdmin)
