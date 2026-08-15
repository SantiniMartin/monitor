from django.urls import path, include
# from django.contrib.auth.views import LogoutView

app_name='evaluaciones_educativas'

urlpatterns = [
    # path('fluidez_2025/', include('apps.evaluaciones_educativas.urls.fluidez_2025', namespace='fluidez_2025')),
    # path('diagnostico_2026/', include('apps.evaluaciones_educativas.urls.diagnostico_2026', namespace='diagnostico_2026')),
    path('fluidez_2026/', include('apps.evaluaciones_educativas.urls.fluidez_2026', namespace='fluidez_2026')),
    # path('omr/', include('apps.evaluaciones_educativas.urls.omr_lector', namespace='omr_lector')),
    path('validaciones_2026/', include('apps.evaluaciones_educativas.urls.validaciones_2026', namespace='validaciones_2026')),
]

