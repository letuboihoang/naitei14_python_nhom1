from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404 
from .forms import SignUpForm, BookingForm, DateSelectionForm 
from django.contrib.auth.decorators import login_required 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
from django.db.models import Q, Exists, OuterRef 
from django.contrib import messages 
from datetime import datetime, date 
import re 
from .utils import send_activation_email, verify_activation_token 
from django.views.decorators.http import require_http_methods, require_POST
from .models import Booking, Facility, Pitch, PitchTimeSlot, PitchType, Voucher, BookingStatus, Favorite
from . import constants 
from django_ratelimit.decorators import ratelimit
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"]) 
def signup(request): 
    if request.method == 'POST': 
        form = SignUpForm(request.POST) 
        if form.is_valid(): 
            try: 
                with transaction.atomic(): 
                    user = form.save(commit=True) 
                    send_activation_email(user, request) 
                    messages.success(
                        request, 
                        'Tài khoản đã được tạo! Vui lòng kiểm tra email để xác thực tài khoản.' 
                    ) 
                    return redirect('login') 
            except Exception as e: 
                logger.error(f'Email sending failed for user {form.cleaned_data.get("email")}', exc_info=True)
                messages.error(
                    request, 
                    'Lỗi gửi email. Vui lòng thử đăng ký lại sau.' 
                ) 
        else: 
            for field, errors in form.errors.items(): 
                for error in errors: 
                    messages.error(request, f'{field}: {error}') 
    else: 
        form = SignUpForm() 
    return render(request, 'registration/sign-up.html', {'form': form})

@ratelimit(key='ip', rate='5/m', block=True)
def activate_account(request, token):
    try:
        success, message = verify_activation_token(token)
        if success:
            messages.success(request, message)
            return redirect('login')
        else:
            messages.error(request, message)
            return redirect('signup')
    except Exception as e:
        logger.error(f'Error activating account', exc_info=True)
        messages.error(request, 'Có lỗi xảy ra. Vui lòng thử lại sau.')
        return redirect('signup')

def home(request): 
    q = request.GET.get("q", "") 
    facilities = Facility.objects.all() 
    if q: 
        facilities = facilities.filter(name__icontains=q) 
    context = { 
        'facilities': facilities, 
        'default_facility_image': constants.DEFAULT_FACILITY_IMAGE, 
    } 
    if request.user.is_authenticated: 
        if request.user.role == constants.ROLE_ADMIN: 
            return render(request, 'host/pitch_manage.html', context) 
        elif request.user.role == constants.ROLE_USER: 
            return render(request, 'main/home.html', context) 
    return render(request, 'main/home.html', context) 

def facility_detail(request, facility_id): 
    facility = get_object_or_404(Facility, id=facility_id) 
    pitches = facility.pitches.filter(is_available=True).select_related('pitch_type')
    
    if request.user.is_authenticated:
        pitch_ids = list(pitches.values_list('id', flat=True))
        
        favorited_pitch_ids = set(Favorite.objects.filter(
            user=request.user,
            pitch_id__in=pitch_ids
        ).values_list('pitch_id', flat=True))
    else:
        favorited_pitch_ids = set()
    
    pitches = list(pitches)
    
    for pitch in pitches:
        pitch.is_favorited = pitch.id in favorited_pitch_ids
    
    context = { 
        'facility': facility, 
        'pitches': pitches, 
        'default_facility_image': constants.DEFAULT_FACILITY_IMAGE, 
        'default_pitch_image': constants.DEFAULT_PITCH_IMAGE, 
        'is_user': request.user.role == constants.ROLE_USER if request.user.is_authenticated else False, 
    } 
    return render(request, 'user/facility_detail.html', context)

def validate_voucher_code(code): 
    if not code: 
        return False, "Mã giảm giá không được để trống" 
    code = code.strip() 
    if len(code) > constants.VOUCHER_CODE_MAX_LENGTH: 
        return False, f"Mã giảm giá không được vượt quá {constants.VOUCHER_CODE_MAX_LENGTH} ký tự" 
    if not re.match(constants.VOUCHER_CODE_PATTERN, code): 
        return False, "Mã giảm giá chỉ được chứa chữ cái, số, dấu gạch ngang và gạch dưới" 
    return True, "" 

def pitch_list(request): 
    pitches = Pitch.objects.select_related('pitch_type', 'facility').all() 
    search_query = request.GET.get('q', '') 
    pitch_type_filter = request.GET.get('pitch_type', '') 
    price_range_filter = request.GET.get('price_range', '') 
    booking_date_filter = request.GET.get('booking_date', '') 
    sort_by = request.GET.get('sort', 'name') 
    
    if search_query: 
        pitches = pitches.filter( 
            Q(name__icontains=search_query) | 
            Q(facility__name__icontains=search_query) | 
            Q(facility__address__icontains=search_query) 
        ) 
    
    if pitch_type_filter: 
        pitches = pitches.filter(pitch_type_id=pitch_type_filter) 
    
    if price_range_filter and price_range_filter in constants.PRICE_RANGES: 
        min_price, max_price = constants.PRICE_RANGES[price_range_filter] 
        if max_price == float('inf'): 
            pitches = pitches.filter(base_price_per_hour__gte=min_price) 
        else: 
            pitches = pitches.filter( 
                base_price_per_hour__gte=min_price, 
                base_price_per_hour__lte=max_price 
            ) 
    
    if booking_date_filter: 
        try: 
            booking_date = datetime.strptime(booking_date_filter, '%Y-%m-%d').date() 
            available_time_slots = PitchTimeSlot.objects.filter( 
                pitch=OuterRef('pk'), 
                is_available=True 
            ).exclude( 
                bookings__booking_date=booking_date, 
                bookings__status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED] 
            ) 
            pitches = pitches.annotate( 
                has_available_slots=Exists(available_time_slots) 
            ).filter( 
                has_available_slots=True, 
                is_available=True 
            ) 
        except ValueError: 
            pass 
    
    if sort_by == 'name': 
        pitches = pitches.order_by('name') 
    elif sort_by == '-name': 
        pitches = pitches.order_by('-name') 
    elif sort_by == 'price': 
        pitches = pitches.order_by('base_price_per_hour') 
    elif sort_by == '-price': 
        pitches = pitches.order_by('-base_price_per_hour') 
    else: 
        pitches = pitches.order_by('name') 
    
    has_filters = any([search_query, pitch_type_filter, price_range_filter, booking_date_filter]) 
    pitch_types = PitchType.objects.all() 
    paginator = Paginator(pitches, constants.ITEMS_PER_PAGE) 
    page_number = request.GET.get('page') 
    
    try: 
        pitches_page = paginator.page(page_number) 
    except PageNotAnInteger: 
        pitches_page = paginator.page(1) 
    except EmptyPage: 
        pitches_page = paginator.page(paginator.num_pages) 
    
    if request.user.is_authenticated:
        pitch_ids = [p.id for p in pitches_page]
        favorited_pitch_ids = set(Favorite.objects.filter(
            user=request.user,
            pitch_id__in=pitch_ids
        ).values_list('pitch_id', flat=True))
    else:
        favorited_pitch_ids = set()
    
    for pitch in pitches_page:
        pitch.is_favorited = pitch.id in favorited_pitch_ids
    
    request_get_dict = dict(request.GET.items())
    
    context = { 
        'pitches': pitches_page, 
        'pitch_types': pitch_types, 
        'has_filters': has_filters, 
        'request_get': request_get_dict, 
        'selected_booking_date': booking_date_filter, 
        'default_pitch_image': constants.DEFAULT_PITCH_IMAGE, 
    } 
    return render(request, 'user/pitch_list.html', context)

@login_required(login_url='login') 
def book_pitch(request, pitch_id): 
    if request.user.role != constants.ROLE_USER: 
        return HttpResponseForbidden("Bạn không có quyền đặt sân!") 
    
    pitch = get_object_or_404(Pitch, id=pitch_id) 
    
    pitch.is_favorited = Favorite.objects.filter(
        user=request.user,
        pitch=pitch
    ).exists()
    
    selected_date = request.GET.get('booking_date', '') 
    voucher_code = request.GET.get('voucher_code', '') 
    date_form = DateSelectionForm(initial={'booking_date': selected_date}) 
    available_time_slots = [] 
    time_slot_choices = [] 
    
    if selected_date: 
        try: 
            booking_date = datetime.strptime(selected_date, '%Y-%m-%d').date() 
            all_pitch_time_slots = PitchTimeSlot.objects.filter( 
                pitch=pitch, 
                is_available=True 
            ).select_related('time_slot') 
                        
            if all_pitch_time_slots.count() == 0: 
                logger.warning(f"No PitchTimeSlots available for pitch {pitch.id}") 
            
            for pitch_time_slot in all_pitch_time_slots: 
                is_available = pitch_time_slot.is_available_on_date(booking_date) 
                
                if is_available: 
                    price = pitch_time_slot.get_price() 
                    slot_data = { 
                        'id': pitch_time_slot.id, 
                        'time_slot': pitch_time_slot.time_slot, 
                        'duration_hours': pitch_time_slot.time_slot.duration_hours(), 
                        'price': price 
                    } 
                    available_time_slots.append(slot_data) 
                    time_slot_choices.append((pitch_time_slot.id, slot_data)) 
            
        except ValueError as e:
            logger.error(f"Invalid date format for booking: {selected_date}", exc_info=True)
            selected_date = '' 
    
    voucher_message = '' 
    voucher_message_type = 'text-muted' 
    if voucher_code: 
        is_valid_format, error_message = validate_voucher_code(voucher_code) 
        
        if not is_valid_format: 
            voucher_message = error_message 
            voucher_message_type = 'text-danger' 
        else: 
            voucher_code_clean = voucher_code.strip().upper() 
            
            try: 
                voucher = Voucher.objects.get(code=voucher_code_clean) 
                if voucher.is_valid(): 
                    voucher_message = f'Mã giảm giá {voucher.discount_percent}% có hiệu lực' 
                    voucher_message_type = 'text-success' 
                else: 
                    voucher_message = 'Mã giảm giá không hợp lệ hoặc đã hết hạn' 
                    voucher_message_type = 'text-danger' 
            except Voucher.DoesNotExist: 
                voucher_message = 'Mã giảm giá không tồn tại' 
                voucher_message_type = 'text-danger' 
    
    booking_form = BookingForm( 
        initial={ 
            'booking_date': selected_date, 
            'voucher_code': voucher_code 
        }, 
        time_slot_choices=time_slot_choices 
    ) 
    
    if request.method == 'POST': 
        booking_form = BookingForm(request.POST, time_slot_choices=time_slot_choices) 
        if booking_form.is_valid(): 
            booking_date = booking_form.cleaned_data['booking_date'] 
            time_slot_id = booking_form.cleaned_data['time_slot'] 
            voucher_code = booking_form.cleaned_data['voucher_code'] 
            note = booking_form.cleaned_data['note'] 
            
            try: 
                pitch_time_slot = PitchTimeSlot.objects.select_related('time_slot').get( 
                    id=time_slot_id, 
                    pitch=pitch 
                ) 
                
                booking = Booking( 
                    user=request.user, 
                    pitch=pitch, 
                    time_slot=pitch_time_slot, 
                    booking_date=booking_date, 
                    note=note 
                ) 
                
                if voucher_code: 
                    is_valid_format, error_message = validate_voucher_code(voucher_code) 
                    
                    if is_valid_format: 
                        voucher_code_clean = voucher_code.strip().upper() 
                        try: 
                            voucher = Voucher.objects.get(code=voucher_code_clean) 
                            if voucher.is_valid(): 
                                booking.voucher = voucher 
                            else: 
                                messages.warning(request, 'Mã giảm giá không hợp lệ, đặt sân không áp dụng giảm giá.') 
                        except Voucher.DoesNotExist: 
                            messages.warning(request, 'Mã giảm giá không tồn tại, đặt sân không áp dụng giảm giá.') 
                    else: 
                        messages.warning(request, f'{error_message}, đặt sân không áp dụng giảm giá.') 
                
                booking.save() 
                messages.success(request, f'Đặt sân thành công! Mã đặt sân: #{booking.id}') 
                logger.info(f"Booking created: #{booking.id} by user {request.user.username}")
                return redirect('pitch_list') 
                
            except (PitchTimeSlot.DoesNotExist, ValueError) as e: 
                logger.error(f"Error creating booking", exc_info=True)
                messages.error(request, 'Có lỗi xảy ra khi đặt sân. Vui lòng thử lại.') 
    
    context = { 
        'pitch': pitch, 
        'selected_date': selected_date, 
        'available_time_slots': available_time_slots, 
        'voucher_code': voucher_code, 
        'voucher_message': voucher_message, 
        'voucher_message_type': voucher_message_type, 
        'today': date.today().isoformat(), 
        'date_form': date_form, 
        'booking_form': booking_form, 
        'default_pitch_image': constants.DEFAULT_PITCH_IMAGE, 
    } 
    
    return render(request, 'user/book_pitch.html', context)

@login_required(login_url='login')
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related(
        'pitch', 
        'pitch__facility', 
        'pitch__pitch_type'
    )
    
    for favorite in favorites:
        favorite.pitch.is_favorited = True
    
    context = {
        'favorites': favorites,
        'is_user': request.user.role == constants.ROLE_USER,
        'default_pitch_image': constants.DEFAULT_PITCH_IMAGE,
    }
    return render(request, 'user/favorite_list.html', context)

@login_required(login_url='login')
@require_POST
def toggle_favorite(request, pitch_id):
    pitch = get_object_or_404(Pitch, id=pitch_id)
    
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        pitch=pitch
    )
    
    if not created:
        favorite.delete()
        is_favorited = False
    else:
        is_favorited = True
    
    if 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'message': 'Đã thêm vào yêu thích' if is_favorited else 'Đã xóa khỏi yêu thích'
        })
    
    return redirect('pitch_list')
