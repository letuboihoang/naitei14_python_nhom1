from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  
    path('sign-up', views.signup, name='signup'), 
    path('activate/<str:token>/', views.activate_account, name='activate_account'),     
    path('book/<int:pitch_id>/', views.book_pitch, name='book_pitch'),  
    path('pitches/', views.pitch_list, name='pitch_list'),  
    path('facility/<int:facility_id>/', views.facility_detail, name='facility_detail'),
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('favorite/toggle/<int:pitch_id>/', views.toggle_favorite, name='toggle_favorite'),
]
