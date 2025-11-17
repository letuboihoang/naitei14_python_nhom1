from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from datetime import datetime, date

# ===== Enum ===================================================
class Role(models.TextChoices):
    USER = "User", "User"
    ADMIN = "Admin", "Admin"
    GUEST = "Guest", "Guest"

class BookingStatus(models.TextChoices):
    PENDING = "Pending", "Đang chờ xác nhận"
    CONFIRMED = "Confirmed", "Đã xác nhận"
    REJECTED = "Rejected", "Bị từ chối"
    CANCELLED = "Cancelled", "Người dùng hủy"

# ===== User ===================================================
class User(AbstractUser):
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    # Activation
    activation_token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    activation_expiry = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

# ===== Facility ===================================================
class Facility(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# ===== Pitch Type ===================================================
class PitchType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# ===== Pitch ===================================================
class Pitch(models.Model):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="pitches",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pitch_type = models.ForeignKey(PitchType, on_delete=models.CASCADE, related_name="pitches")
    base_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    images = models.JSONField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        facility_name = self.facility.name if self.facility else "No Facility"
        return f"{self.name} - {facility_name}"

# ===== Voucher ===================================================
class Voucher(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_percent = models.PositiveIntegerField(default=0)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Validate voucher dates"""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Ngày bắt đầu phải trước ngày kết thúc.")

    def is_valid(self):
        """Check if voucher is valid for use"""
        today = date.today()
        
        if not self.is_active:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        return True

    def __str__(self):
        return self.code

# ===== Booking ===================================================
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    pitch = models.ForeignKey(Pitch, on_delete=models.CASCADE, related_name="bookings")
    
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    
    voucher = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pitch', 'booking_date', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def calculate_duration(self):
        """Calculate duration in hours"""
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        return (end - start).total_seconds() / 3600

    def calculate_final_price(self):
        """Calculate final price with voucher discount"""
        base_price = self.duration_hours * float(self.pitch.base_price_per_hour)
        
        if self.voucher and self.voucher.is_valid():
            if self.voucher.min_order_value is None or base_price >= float(self.voucher.min_order_value):
                discount = base_price * (self.voucher.discount_percent / 100)
                return base_price - discount
        return base_price

    def clean(self):
        """Basic validation"""
        errors = {}

        # Date validation
        if self.booking_date and self.booking_date < date.today():
            errors['booking_date'] = "Không thể đặt lịch trong quá khứ."

        # Time validation
        duration = self.calculate_duration()
        if duration <= 0:
            errors['end_time'] = "Giờ kết thúc phải sau giờ bắt đầu."
        elif duration < 1.5:
            errors['end_time'] = "Thời gian tối thiểu là 1 giờ 30 phút."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Auto-calculate duration and price before saving"""
        # Calculate duration
        self.duration_hours = self.calculate_duration()
        
        # Calculate final price
        self.final_price = self.calculate_final_price()
        
        # Run validation
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pitch.name} - {self.user.username} ({self.booking_date})"

# ===== Review ===================================================
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    pitch = models.ForeignKey(Pitch, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # Rating from 1-5
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'pitch')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pitch', 'rating']),
        ]

    def __str__(self):
        return f"Review by {self.user.username} for {self.pitch.name} - {self.rating} stars"

# ===== Comment ===================================================
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="comments")
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on review {self.review.id}"

# ===== Favorite ===================================================
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    pitch = models.ForeignKey(Pitch, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "pitch")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} favorites {self.pitch.name}"
    