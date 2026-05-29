"""
URL configuration for monitoreo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from apps.evaluaciones_educativas.views import diagnostico_2026

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('', diagnostico_2026.monitoreo_evaluaciones_educativas_establecimientos, name='monitoreo_diagnostico'),
    path('', diagnostico_2026.monitoreo_evaluaciones_educativa_alumnos, name='monitoreo_diagnostico_alumno'),
    path('monitoreo_diagnostico_seccion/', diagnostico_2026.monitoreo_evaluaciones_educativa_seccion, name='monitoreo_diagnostico_seccion'),
    path('borrar/', diagnostico_2026.borrar_alumno, name='borrar_alumno'),
    #path('descargar_excel/',diagnostico_2026.descargar_excel, name='excel'),

]
