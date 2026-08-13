from django.contrib import admin

# Register your models here.
from .models.fluidez_2026 import *
from .models.validaciones_2026 import (
    ValReferenteCargaTemporal,
    ValEstablecimiento,
    ValGrado,
    ValCabecera,
    ValSeccion,
    ValHistorialMatriculas,
    ValHistorialCambiosEstablecimiento,
)

# ── Fluidez 2026 ──────────────────────────────────────────────
admin.site.register(EstablecimientosFluidez2026)
admin.site.register(AlumnoFluidez2026)
admin.site.register(GradoFluidez2026)
admin.site.register(EvaluacionFluidezLectoraFluidez2026)
admin.site.register(SeccionFluidez2026)

# ── Validaciones 2026 ─────────────────────────────────────────
@admin.register(ValReferenteCargaTemporal)
class ValReferenteCargaTemporalAdmin(admin.ModelAdmin):
    list_display = ('cuil', 'apellido', 'nombre', 'region')
    search_fields = ('cuil', 'apellido', 'nombre', 'region')
    list_filter = ('region',)

@admin.register(ValEstablecimiento)
class ValEstablecimientoAdmin(admin.ModelAdmin):
    list_display = ('cueanexo', 'escuela', 'region', 'localidad', 'departamento')
    search_fields = ('cueanexo', 'escuela', 'region')
    list_filter = ('region', 'sector', 'ambito')

@admin.register(ValGrado)
class ValGradoAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'nombre_grado', 'establecimiento', 'cueanexo', 'estado_carga')
    search_fields = ('cueanexo', 'establecimiento__escuela')
    list_filter = ('nombre_grado', 'estado_carga')

@admin.register(ValCabecera)
class ValCabeceraAdmin(admin.ModelAdmin):
    list_display = ('nombre_cabecera', 'regional', 'localidad', 'nombre_coordinador', 'cuil_coordinador')
    search_fields = ('nombre_cabecera', 'regional', 'cuil_coordinador')
    list_filter = ('regional',)

@admin.register(ValSeccion)
class ValSeccionAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'seccion', 'turno', 'grado', 'matricula', 'estado_validacion', 'cabecera')
    search_fields = ('seccion', 'grado__establecimiento__escuela')
    list_filter = ('estado_validacion', 'turno', 'seccion')
    readonly_fields = ('public_id', 'fecha_ultima_modificacion')

@admin.register(ValHistorialMatriculas)
class ValHistorialMatriculasAdmin(admin.ModelAdmin):
    list_display = ('seccion', 'matricula_anterior', 'matricula_nueva', 'usuario_cambio', 'fecha_cambio')
    search_fields = ('seccion__grado__establecimiento__escuela', 'usuario_cambio')
    readonly_fields = ('fecha_cambio',)

@admin.register(ValHistorialCambiosEstablecimiento)
class ValHistorialCambiosEstablecimientoAdmin(admin.ModelAdmin):
    list_display = ('establecimiento', 'usuario', 'fecha')
    search_fields = ('establecimiento__escuela', 'usuario')
    readonly_fields = ('fecha',)