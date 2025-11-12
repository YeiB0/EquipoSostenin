from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('subir/', views.subir_boleta_view, name='subir_boleta'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
