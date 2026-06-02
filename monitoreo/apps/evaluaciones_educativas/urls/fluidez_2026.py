from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_2026

app_name = 'fluidez_2026' 

urlpatterns = [
	path('',fluidez_2026.inicio, name= 'inicio'),
]