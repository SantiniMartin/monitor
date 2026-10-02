from django.urls import path, include
from apps.evaluaciones_educativas.views import dashboard

app_name='evaluaciones_educativas'

urlpatterns = [
    path('', dashboard.dashboard, name='dashboard'),
    #path('fluidez_2025/', include('apps.evaluaciones_educativas.urls.fluidez_2025', namespace='fluidez_2025')),
    # path('fluidez_octubre_2026/', include('apps.evaluaciones_educativas.urls.fluidez_octubre_2026', namespace='fluidez_octubre_2026')),
    #path('diagnostico_2026/', include('apps.evaluaciones_educativas.urls.diagnostico_2026', namespace='diagnostico_2026')),
    path('fluidez_2026/', include('apps.evaluaciones_educativas.urls.fluidez_2026', namespace='fluidez_2026')),
    #path('diagnostico_2025/', include('apps.evaluaciones_educativas.urls.diagnostico_2025', namespace='diagnostico_2025')),
    #path('validaciones_2026/', include('apps.evaluaciones_educativas.urls.validaciones_2026', namespace='validaciones_2026')),
]

