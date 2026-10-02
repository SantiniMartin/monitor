from django import forms
from apps.evaluaciones_educativas.models.fluidez_octubre_2026 import *


# class CueanexoFluidezOctubre2026ViewForm(forms.Form):
# 	cueanexo = forms.ChoiceField(
# 		choices=[('', '--- Seleccionar ---')],
# 		label='SELECCIONE UN CUEANEXO', 
# 		required=False,
# 		widget=forms.Select
# 	)
# 	def __init__(self, *args, **kwargs):
# 		cuil = kwargs.pop('cuil', None)
# 		super().__init__(*args, **kwargs)
# 		if cuil:
# 			qs = TablaTemporalAplicadoresFluidezOctubre2026.objects.filter(cuil=cuil).only('cueanexo').distinct()
# 			choices_cueanexo = [
# 					('', '---SELECCIONE UN CUEANEXO-----'),
# 					]
# 			for i in qs:
# 				choices_cueanexo.append((i.cueanexo, i.cueanexo))
# 			self.fields['cueanexo'].choices = choices_cueanexo


# class GradoFluidezOctubre2026ViewForm(forms.Form):
# 	grado = forms.ChoiceField(label='SELECCIONE UN GRADO', required=False, widget=forms.RadioSelect())
# 	def __init__(self, *args, **kwargs):
# 		cueanexo = kwargs.pop('cueanexo', None)
# 		super().__init__(*args, **kwargs)
# 		if cueanexo:
# 			grados_permitidos=['2do Año/Grado','3er Año/Grado']
# 			# print('entre')
# 			# qs=V_Trayectoria_Alumnos_SGE.objects.using('test').filter(cueanexo=cueanexo,anio_grado__in=grados_permitidos ).values_list('anio_grado').distinct()
# 			# print(qs)
# 			choices_grado = []
# 			for i in grados_permitidos:
# 				choices_grado.append((i, i))
# 			self.fields['grado'].choices = choices_grado


# class AlumnoFluidezOctubre2026Form(forms.Form):	
# 		fields = ['dni', 'nombre', 'apellido', 'comunidad_indigena', 'discapacidad']
# 		widgets = {
# 			'dni': forms.TextInput(attrs={
# 				'required': 'true',         
# 				'minlength': '8',
# 				'maxlength': '8',
# 				'placeholder': 'INGRESA EL DNI DEL ALUMNO',
# 				'pattern': '[0-9]*'
# 			}),
# 			'nombre': forms.TextInput(attrs={
# 				'required': 'true', 
# 				'placeholder': 'NOMBRE DEL ALUMNO EN MAYUSCULA',
# 				'pattern': '[A-ZÑÁÉÍÓÚ ]*'
# 			}),
# 			'apellido': forms.TextInput(attrs={
# 				'required': 'true', 
# 				'placeholder': 'APELLIDO DEL ALUMNO EN MAYUSCULA',
# 				'pattern': '[A-ZÑÁÉÍÓÚ ]*'
# 			}),
# 			'comunidad_indigena': forms.Select(
# 				attrs={'required': 'true'}),
# 			'discapacidad': forms.Select(
# 				attrs={'required': 'true'})
# 			}


# class AsistenciaFluidezOctubre2026Form(forms.Form):
# 	asistencia = forms.BooleanField(label='ASISTENCIA', required=False,
# 		widget=forms.RadioSelect(
# 			choices=[
# 				(True, '✅ ASISTIO'), 
# 				(False, '❌ NO ASISTIO ')
# 			]
# 		)
# 	)


# class EvaluacionFluidezOctubre2026Form(forms.ModelForm):
# 	class Meta:
# 		model = Fluidez_Lectora_Octubre_2026
# 		fields = ['asistencia', 'cantidad_palabras_leidas', 'pregunta_1', 'pregunta_2', 'pregunta_3', 'pregunta_4', 'pregunta_5', 'pregunta_6']
# 		widgets = {
# 			'asistencia': forms.Select(
# 				attrs={'required': 'true'}),
# 			'cantidad_palabras_leidas': forms.NumberInput(attrs={
# 				'min': '0',
# 				'placeholder': 'INGRESA LA CANTIDAD DE PALABRAS LEIDAS'
# 			}),
# 			'pregunta_1': forms.Select(attrs={'required': 'true'}),
# 			'pregunta_2': forms.Select(attrs={'required': 'true'}),
# 			'pregunta_3': forms.Select(attrs={'required': 'true'}),
# 			'pregunta_4': forms.Select(attrs={'required': 'true'}),
# 			'pregunta_5': forms.Select(attrs={'required': 'true'}),
# 			'pregunta_6': forms.Select(attrs={'required': 'true'}),
# 		}

# 	def __init__(self, *args, max_cantidad_palabra=None, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		if max_cantidad_palabra is not None:
# 			self.fields['cantidad_palabras_leidas'].max_value = max_cantidad_palabra
# 			self.fields['cantidad_palabras_leidas'].widget.attrs['max'] = max_cantidad_palabra
# 			self.fields['cantidad_palabras_leidas'].widget.attrs['placeholder'] = f'Máx. {max_cantidad_palabra}'
# 		if self.is_bound and self.data.get('asistencia') == 'AUSENTE':
# 			campos_dependientes = [
# 				'cantidad_palabras_leidas', 'pregunta_1', 'pregunta_2', 
# 				'pregunta_3', 'pregunta_4', 'pregunta_5', 'pregunta_6'
# 			]
# 			for campo in campos_dependientes:
# 				self.fields[campo].required = False

# 	def clean(self):
# 		cleaned_data = super().clean()
# 		asistencia = cleaned_data.get('asistencia')
# 		if asistencia == 'AUSENTE':
# 			campos_dependientes = [
# 				'cantidad_palabras_leidas', 'pregunta_1', 'pregunta_2', 
# 				'pregunta_3', 'pregunta_4', 'pregunta_5', 'pregunta_6'
# 			]
# 			for campo in campos_dependientes:
# 				cleaned_data[campo] = None
# 				if campo in self._errors:
# 					del self._errors[campo]
# 		return cleaned_data


# class GradoFluidezOctubre2026Form(forms.Form):
# 	class Meta:
# 		fields = ['nombre_grado', 'cueanexo']
# 		widgets = {
# 			'cueanexo': forms.NumberInput(
# 				attrs={'readonly': 'readonly'}
# 			),
# 			'nombre_grado': forms.TextInput(
# 				attrs={'readonly': 'readonly'}
# 			),
# 		}


# class SeccionFluidezOctubre2026Form(forms.Form):
	
# 	seccion_turno = forms.ChoiceField(
# 		choices=[('', '--- Seleccionar turno y sección ---')],
# 		label='SELECCIONE TURNO Y SECCIÓN', 
# 		required=False,
# 		widget=forms.Select
# 	)
# 	def __init__(self, *args, **kwargs):
# 		cueanexo = kwargs.pop('cueanexo', None)
# 		nombre_grado = kwargs.pop('nombre_grado', None)
# 		super().__init__(*args, **kwargs)
# 		if cueanexo and nombre_grado:
# 			qs = SeccionFluidez2026.objects.filter(
# 				grado__cueanexo=cueanexo, grado__nombre_grado=nombre_grado
# 			).values_list('id', 'seccion', 'turno')
# 			choices_seccion_turno = [
# 					('', '---SELECCIONE TURNO Y SECCIÓN-----'),
# 					]
# 			for i in qs:
# 				choices_seccion_turno.append((i[0], (f'Sección: {i[1]} Turno: {i[2]}')))
# 			self.fields['seccion_turno'].choices = choices_seccion_turno


# class BorrarRegistroAlumnoOctubre2026Form(forms.Form):
# 	borrar = forms.BooleanField(label='borrar', required=False,
# 		widget=forms.RadioSelect(
# 			choices=[
# 				(True, 'Eliminar registro'), 
# 				(False, 'NO eliminar registro ')
# 			]
# 		)
# 	)


#----------------------tabuladores------------------------------------

import re

class TabuladorFluidezOctubreForm(forms.ModelForm):
    class Meta:
        model = TabuladoresFluidezOctubre2026
        fields = ['cuil', 'apellido', 'nombre', 'correo', 'celular']
        labels = {
            'cuil':     'CUIL (sin guiones)',
            'apellido': 'Apellido',
            'nombre':   'Nombre',
            'correo':   'Correo electrónico',
            'celular':  'Celular',
        }
        widgets = {
            'cuil': forms.TextInput(attrs={
                'placeholder': 'Ej: 20123456789',
                'maxlength':   '11',
                'minlength':   '10',
                'pattern':     '[0-9]+',
                'inputmode':   'numeric',
            }),
            'apellido': forms.TextInput(attrs={
                'placeholder': 'Apellido del tabulador',
            }),
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Nombre del tabulador',
            }),
            'correo': forms.EmailInput(attrs={
                'placeholder': 'correo@ejemplo.com',
            }),
            'celular': forms.TextInput(attrs={
                'placeholder': 'Ej: 3804123456',
            }),
        }

    def clean_cuil(self):
        cuil = self.cleaned_data.get('cuil', '').strip()
        if not cuil.isdigit():
            raise forms.ValidationError('El CUIL debe contener solo dígitos, sin guiones ni espacios.')
        if len(cuil) < 10 or len(cuil) > 11:
            raise forms.ValidationError('El CUIL debe tener entre 10 y 11 dígitos.')
        # Verificar unicidad solo en creación (pk no existe aún)
        if TabuladoresFluidezOctubre2026.objects.filter(cuil=cuil).exists():
            raise forms.ValidationError('Ya existe un tabulador registrado con ese CUIL.')
        return cuil

    def clean_apellido(self):
        val = self.cleaned_data.get('apellido', '').strip()
        if not val:
            raise forms.ValidationError('El apellido es obligatorio.')
        return val.upper()

    def clean_nombre(self):
        val = self.cleaned_data.get('nombre', '').strip()
        if not val:
            raise forms.ValidationError('El nombre es obligatorio.')
        return val.upper()

    def clean_celular(self):
        val = self.cleaned_data.get('celular', '').strip()
        if not val:
            raise forms.ValidationError('El celular es obligatorio.')
        # Rechazar explícitamente letras
        if re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', val):
            raise forms.ValidationError('El celular no puede contener letras.')
        # Solo dígitos, espacios, guiones, +, paréntesis
        if not re.match(r'^[\d\s\-\+\(\)]+$', val):
            raise forms.ValidationError('Ingresá un número de celular válido (solo dígitos).')
        # Normalizar: quedarse solo con los dígitos para guardar
        solo_digitos = re.sub(r'[^\d]', '', val)
        if len(solo_digitos) < 6:
            raise forms.ValidationError('El celular debe tener al menos 6 dígitos.')
        return val

    def clean_correo(self):
        val = self.cleaned_data.get('correo', '').strip()
        if not val:
            return None
        # Validación explícita de formato de email
        email_regex = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, val):
            raise forms.ValidationError('Ingresá una dirección de correo válida (ej: nombre@dominio.com).')
        # Validar que no tenga espacios
        if ' ' in val:
            raise forms.ValidationError('El correo no puede contener espacios.')
        return val.lower()


def obtener_regional(cuil):
	db_params = conexion_bd()
	conn = None
	regional= None

	 #consutla a select * from public.usuarios_regionalusuarios where usuario=cuil_con_caracter
	try:
		# 1. Establecer la conexión
		#ERROR AQUI
		conn = psycopg2.connect(**db_params)
		
		# 2. Crear el cursor (usamos RealDictCursor para traer nombres de columnas)
		with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
			if cuil:
				cuil_string=f'{cuil}'
				#print(cuil_string)
				query_regiones=f"""
						SELECT region_loc
						FROM public.usuarios_regionalusuarios
						WHERE usuario = %s
						"""
				cur.execute(query_regiones,(cuil_string,))
				regional_datos = cur.fetchall()
				regional=[]
				for fila in regional_datos:
					#print(fila['region_loc'])
					regional.append(fila['region_loc'])
	except (Exception, psycopg2.DatabaseError) as error:
	# 5. Manejo de errores
		print(f"Error al conectar o consultar: {error}")

	finally:
		# 6. Cerrar la conexión pase lo que pase
		if conn is not None:
			conn.close()
			print("Conexión cerrada.") 
	#print(regional)
	return regional