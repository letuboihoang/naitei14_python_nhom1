from django.contrib import admin
from .models import (
    User,
    Facility,
    PitchType,
    Pitch,
    Voucher,
    Booking,
    Review,
    Comment,
    Favorite,
)

# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "username",
        "email",
        "full_name",
        "role",
        "is_active",
        "created_at",
    ]
    list_filter = ["role", "is_active", "created_at"]
    search_fields = ["username", "email", "full_name"]
    date_hierarchy = "created_at"


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ["name", "address", "created_at"]
    search_fields = ["name", "address"]


@admin.register(PitchType)
class PitchTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]


@admin.register(Pitch)
class PitchAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "facility",
        "pitch_type",
        "base_price_per_hour",
        "is_available",
        "created_at",
    ]
    list_filter = ["pitch_type", "is_available", "facility"]
    search_fields = ["name", "address"]
    date_hierarchy = "created_at"


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "discount_percent",
        "usage_limit",
        "used_count",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["is_active", "start_date", "end_date"]
    search_fields = ["code", "description"]
    readonly_fields = ["used_count"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "pitch",
        "user",
        "booking_date",
        "start_time",
        "end_time",
        "duration_hours",
        "final_price",
        "status",
        "created_at",
    ]
    list_filter = ["status", "booking_date", "created_at"]
    search_fields = ["user__username", "pitch__name"]
    date_hierarchy = "booking_date"
    readonly_fields = [
        "duration_hours",
        "final_price",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Thông tin cơ bản",
            {
                "fields": (
                    "user",
                    "pitch",
                    "booking_date",
                    "start_time",
                    "end_time",
                )
            },
        ),
        (
            "Giá và Voucher",
            {
                "fields": (
                    "duration_hours",
                    "final_price",
                    "voucher",
                )
            },
        ),
        (
            "Trạng thái",
            {
                "fields": (
                    "status",
                    "note",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "pitch", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["user__username", "pitch__name", "content"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["user", "review", "parent_comment", "created_at"]
    search_fields = ["user__username", "content"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "pitch", "created_at"]
    search_fields = ["user__username", "pitch__name"]
