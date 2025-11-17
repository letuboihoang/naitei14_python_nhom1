from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignUpForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Pitch
def home(request):
    pitches = Pitch.objects.all() 
    context = {
        'pitches': pitches,
        'user_role': request.user.role if request.user.is_authenticated else None,
        'is_admin': request.user.is_authenticated and request.user.role == "Admin",
        'is_user': request.user.is_authenticated and request.user.role == "User"
    }
    
    if request.user.is_authenticated:
        if request.user.role == "Admin":
            return render(request, 'host/pitch_manage.html', context)
        elif request.user.role == "User":
            return render(request, 'user/pitch_list.html', context)
    return render(request, 'main/home.html', context)

def sign_up(request):
        if request.method == 'POST':
                form = SignUpForm(request.POST)
                if form.is_valid():
                        user = form.save()
                        login(request, user)
                        return redirect('home')
        else:
                form = SignUpForm()
        return render(request, 'registration/sign-up.html', {'form': form})
    
def pitch_list(request):
    pitches = Pitch.objects.all()
    
    paginator = Paginator(pitches, 4)  
    page_number = request.GET.get('page')
    
    try:
        pitches = paginator.page(page_number)
    except PageNotAnInteger:
        pitches = paginator.page(1)
    except EmptyPage:
        pitches = paginator.page(paginator.num_pages)
    
    context = {
        'pitches': pitches,
        'user_role': request.user.role if request.user.is_authenticated else None,
        'is_admin': request.user.is_authenticated and request.user.role == "Admin",
        'is_user': request.user.is_authenticated and request.user.role == "User"
    }
    
    return render(request, 'user/pitch_list.html', context)

@login_required(login_url='login')
def book_pitch(request, pitch_id):
    if request.user.role != "User":
        return HttpResponseForbidden("Bạn không có quyền đặt sân!")

    pitch = get_object_or_404(Pitch, id=pitch_id)
    context = {
        'pitch': pitch,
        'user_role': request.user.role,
        'is_admin': request.user.role == "Admin",
        'is_user': request.user.role == "User"
    }
    return render(request, 'user/book_pitch.html', context)
