# from django import forms
# from apps.evaluaciones_educativas.models.diagnostico_2026 import *
# from apps.consultasge.models import CapaUnicaOfertas
# import psycopg2
# import os
# from psycopg2 import extras

from django import forms
from ..models import Matematica2026, Lengua2026, Alumno2026


class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno2026
        fields = ['dni', 'nombre', 'apellido', 'comunidad_indigena', 'discapacidad']
        widgets = {
            'dni': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 12345678',
                'minlength': '7',
                'maxlength': '8',
                'pattern': '[0-9]*'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre en mayúsculas',
                'pattern': '[A-ZÑÁÉÍÓÚ ]*'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido en mayúsculas',
                'pattern': '[A-ZÑÁÉÍÓÚ ]*'
            }),
            'comunidad_indigena': forms.Select(attrs={'class': 'form-select'}),
            'discapacidad': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_dni(self):
        """Validar que el DNI no exista en la base de datos."""
        dni = self.cleaned_data.get('dni')
        if dni:
            # Si es actualización, excluir el alumno actual
            existing = Alumno2026.objects.filter(dni=dni)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError('Ya existe un alumno con ese DNI')
        return dni


class SeleccionarMateriaForm(forms.Form):
    materia = forms.ChoiceField(
        choices=[
            ('matematica', 'Matemática'),
            ('lengua', 'Lengua'),
        ],
        label='Seleccione la materia del examen',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )


class MatematicaForm(forms.ModelForm):
    class Meta:
        model = Matematica2026
        fields = [
            'modelo',
            'asistencia',
            'encargado_carga',
            'pregunta_1',
            'pregunta_2',
            'pregunta_3',
            'pregunta_4',
            'pregunta_5',
            'pregunta_6',
            'pregunta_7',
            'pregunta_8',
            'pregunta_9',
            'pregunta_10',
            'pregunta_11',
            'pregunta_12',
        ]
        widgets = {
            'asistencia': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'modelo': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'encargado_carga': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encargado_carga'].required = False
        for field_name, field in self.fields.items():
            if field_name.startswith('pregunta_'):
                field.required = False  # ← siempre opcionales
                field.widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        asistencia = cleaned_data.get('asistencia')
        
        if asistencia == 'AUSENTE':
            # Si está ausente, forzamos None en todas las preguntas
            for field_name in self.fields:
                if field_name.startswith('pregunta_'):
                    cleaned_data[field_name] = None
                    
        elif asistencia == 'PRESENTE':
            # Si está presente, todas las preguntas son obligatorias
            campos_vacios = []
            for field_name in self.fields:
                if field_name.startswith('pregunta_'):
                    valor = cleaned_data.get(field_name)
                    if not valor:
                        # Transformamos 'pregunta_2' en 'Pregunta 2' antes de guardarlo en la lista
                        nombre_legible = field_name.replace('_', ' ').capitalize()
                        campos_vacios.append(nombre_legible)
                        
            if campos_vacios:
                raise forms.ValidationError(
                    f'El alumno está presente. Debe completar todas las preguntas. '
                    f'Faltan: {", ".join(campos_vacios)}'
                )
                
        return cleaned_data

class LenguaForm(forms.ModelForm):
    class Meta:
        model = Lengua2026
        fields = [
            'modelo',
            'asistencia',
            'encargado_carga',
            'pregunta_1',
            'pregunta_2',
            'pregunta_3',
            'pregunta_4',
            'pregunta_5',
            'pregunta_6',
            'pregunta_7',
            'pregunta_8',
            'pregunta_9',
            'pregunta_10',
            'pregunta_11_1',
            'pregunta_11_2',
            'pregunta_11_3',
            'pregunta_11_4',
            'pregunta_12',
            'pregunta_13',
            'pregunta_14',
            'pregunta_15',
            'pregunta_16',
            'pregunta_17',
            'pregunta_18',
            'pregunta_19',
            'pregunta_20',
            'pregunta_21',
            'pregunta_22_1',
            'pregunta_22_2',
            'pregunta_22_3',
        ]
        widgets = {
            'asistencia': forms.Select(attrs={'class': 'form-select',}),
            'modelo': forms.Select(attrs={'class': 'form-select',}),
            'encargado_carga': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encargado_carga'].required = False
        for field_name, field in self.fields.items():
            if field_name.startswith('pregunta_'):
                field.required = False  # ← siempre opcionales
                field.widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        asistencia = cleaned_data.get('asistencia')
        
        if asistencia == 'AUSENTE':
            # Si está ausente, forzamos None en todas las preguntas
            for field_name in self.fields:
                if field_name.startswith('pregunta_'):
                    cleaned_data[field_name] = None
                    
        elif asistencia == 'PRESENTE':
            # Si está presente, todas las preguntas son obligatorias
            campos_vacios = []
            for field_name in self.fields:
                if field_name.startswith('pregunta_'):
                    valor = cleaned_data.get(field_name)
                    if not valor:
                        # Transformamos 'pregunta_2' en 'Pregunta 2' antes de guardarlo en la lista
                        nombre_legible = field_name.replace('_', ' ').capitalize()
                        campos_vacios.append(nombre_legible)
                        
            if campos_vacios:
                raise forms.ValidationError(
                    f'El alumno está presente. Debe completar todas las preguntas. '
                    f'Faltan: {", ".join(campos_vacios)}'
                )
                
        return cleaned_data

# class MatematicaForm(forms.ModelForm):
#     class Meta:
#         model = Matematica2026
#         # Incluimos los campos de la clase base y la hija
#         fields = [
#             'asistencia', 'modelo', 'encargado_carga',
#             'pregunta_1', 'pregunta_2', 'pregunta_3', 'pregunta_4', 
#             'pregunta_5', 'pregunta_6', 'pregunta_7', 'pregunta_8', 
#             'pregunta_9', 'pregunta_10', 'pregunta_11', 'pregunta_12'
#         ]
#         widgets = {
#             # Podemos añadir clases de Bootstrap para que se vea bien
#             field: forms.Select(attrs={'class': 'form-select'}) 
#             for field in fields if field != 'encargado_carga'
#         }

# class LenguaForm(forms.ModelForm):
#     class Meta:
#         model = Lengua2026
#         fields = [
#             'asistencia', 'modelo', 'encargado_carga',
#             'pregunta_1', 'pregunta_2', 'pregunta_3', 'pregunta_4', 'pregunta_5',
#             'pregunta_6', 'pregunta_7', 'pregunta_8', 'pregunta_9', 'pregunta_10',
#             'pregunta_11_1', 'pregunta_11_2', 'pregunta_11_3', 'pregunta_11_4',
#             'pregunta_12', 'pregunta_13', 'pregunta_14', 'pregunta_15', 'pregunta_16',
#             'pregunta_17', 'pregunta_18', 'pregunta_19', 'pregunta_20', 'pregunta_21',
#             'pregunta_22_1', 'pregunta_22_2', 'pregunta_22_3'
#         ]
#         widgets = {
#             field: forms.Select(attrs={'class': 'form-select'}) 
#             for field in fields if field != 'encargado_carga'
#         }

# class MatematicaForm(forms.ModelForm):
#     class Meta:
#         model = Matematica2026
#         # Excluimos el alumno del formulario de creación
#         exclude = ['alumno'] 
#         widgets = {
#             field: forms.Select(attrs={'class': 'form-control'}) 
#             for field in self.Meta.model._meta.get_fields() # lógica para automatizar widgets
#         }

# from django import forms
# from ..models import Matematica2026, Lengua2026

# class MatematicaForm(forms.ModelForm):
#     class Meta:
#         model = Matematica2026
#         exclude = ['alumno'] # No pedimos el alumno al crear el examen
#         widgets = {
#             'nombre_examen': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre descriptivo'}),
#             'asistencia': forms.Select(attrs={'class': 'form-select'}),
#             'modelo': forms.Select(attrs={'class': 'form-select'}),
#             'encargado_carga': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
#         }
#         # Agregamos dinámicamente el estilo a las preguntas
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         for field in self.fields:
#             if 'pregunta_' in field:
#                 self.fields[field].widget.attrs.update({'class': 'form-select'})

# class LenguaForm(forms.ModelForm):
#     class Meta:
#         model = Lengua2026
#         exclude = ['alumno']
#         widgets = {
#             'nombre_examen': forms.TextInput(attrs={'class': 'form-control'}),
#             'asistencia': forms.Select(attrs={'class': 'form-select'}),
#             'modelo': forms.Select(attrs={'class': 'form-select'}),
#         }
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         for field in self.fields:
#             if 'pregunta_' in field:
#                 self.fields[field].widget.attrs.update({'class': 'form-select'})

# class AñoViewForm(forms.Form):
# 	año= forms.ChoiceField(label='SELECCIONE UN AÑO', required=False, widget=forms.RadioSelect(
# 		))

# class SeccionViewForm(forms.Form):
# 	seccion= forms.ChoiceField(label='secciones', required=False)


# class AlumnoForm(forms.ModelForm):

# 	class Meta:
# 		model = Alumno2026
# 		fields = ['dni','nombre','apellido','comunidad_indigena' ,'discapacidad']
# 		#widget  para cambiar tipo de campo
# 		widgets = {
# 			'dni': forms.TextInput(attrs={
# 				'required': 'true',         
# 				'minlength': '8',
# 				'maxlength':'8',
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
# 		#label para cambiar nombre de campo

# class AsistenciaForm(forms.Form):
# 	asistencia= forms.BooleanField(label='ASISTENCIA', required=False,
# 		widget=forms.RadioSelect(
# 			choices=[
# 				(True,'✅ ASISTIO'), 
# 				(False, '❌ NO ASISTIO ')
# 			]
# 		)
# 	)

# class EvaluacionLenguaForm(forms.ModelForm):
# 	class Meta:
# 		model= Lengua2026
# 		fields=['cantidad_palabras_leidas','pregunta_1','pregunta_2','pregunta_3','pregunta_4' ,'pregunta_5','pregunta_6']
# 		widgets = {
# 			'cantidad_palabras_leidas': forms.NumberInput(attrs={
# 			'min':'0',
# 			'placeholder':'INGRESA LA CANTIDAD DE PALABRAS LEIDAS'
# 			}),
# 			'pregunta_1': forms.Select(
# 				attrs={'required': 'true'}),
# 			'pregunta_2': forms.Select(
# 				attrs={'required': 'true'})
# 				,'pregunta_3': forms.Select(
# 				attrs={'required': 'true'}),
# 			'pregunta_4': forms.Select(
# 				attrs={'required': 'true'})
# 				,'pregunta_5': forms.Select(
# 				attrs={'required': 'true'}),
# 			'pregunta_6': forms.Select(
# 				attrs={'required': 'true'})
# 			}
		
# 	def __init__(self, *args, max_cantidad_palabra=None, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		if max_cantidad_palabra is not None:
# 			# Establece el tope de validación en el nivel del formulario
# 			self.fields['cantidad_palabras_leidas'].max_value = max_cantidad_palabra 
			
# 			# **Importante:** Establece el atributo HTML 'max' para el frontend
# 			self.fields['cantidad_palabras_leidas'].widget.attrs['max'] = max_cantidad_palabra
# 			self.fields['cantidad_palabras_leidas'].widget.attrs['placeholder'] = f'Máx. {max_cantidad_palabra}'

# class EvaluacionMatematicaForm(forms.ModelForm):
# 	class Meta:
# 		model= Matematica2026
# 		fields=['cantidad_palabras_leidas','pregunta_1','pregunta_2','pregunta_3','pregunta_4' ,'pregunta_5','pregunta_6']
# 		widgets = {
# 			'cantidad_palabras_leidas': forms.NumberInput(attrs={
# 			'min':'0',
# 			'placeholder':'INGRESA LA CANTIDAD DE PALABRAS LEIDAS'
# 			}),
# 			'pregunta_1': forms.Select(
# 				attrs={'required': 'true'}),
# 			'pregunta_2': forms.Select(
# 				attrs={'required': 'true'})
# 				,'pregunta_3': forms.Select(
# 				attrs={'required': 'true'}),
# 			'pregunta_4': forms.Select(
# 				attrs={'required': 'true'})
# 				,'pregunta_5': forms.Select(
# 				attrs={'required': 'true'}),
# 			'pregunta_6': forms.Select(
# 				attrs={'required': 'true'})
# 			}
		
# 	def __init__(self, *args, max_cantidad_palabra=None, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		if max_cantidad_palabra is not None:
# 			# Establece el tope de validación en el nivel del formulario
# 			self.fields['cantidad_palabras_leidas'].max_value = max_cantidad_palabra 
			
# 			# **Importante:** Establece el atributo HTML 'max' para el frontend
# 			self.fields['cantidad_palabras_leidas'].widget.attrs['max'] = max_cantidad_palabra
# 			self.fields['cantidad_palabras_leidas'].widget.attrs['placeholder'] = f'Máx. {max_cantidad_palabra}'

# class AñoForm(forms.ModelForm):
# 	class Meta:
# 		model = Año2026
# 		fields=['nombre_año','cueanexo']
# 		#ocultamos cueanexo
# 		widgets = {
# 			'cueanexo': forms.NumberInput(
# 				attrs={
# 					'readonly':'readonly'
# 				}
# 			),
# 			'nombre_grado': forms.TextInput(
# 				attrs={
# 					'readonly':'readonly'
# 				}
# 			),
# 			}
# 	#solucion para evitar no seleccionar un unique desde el form	


# class SeccionForm(forms.ModelForm):
# 	class Meta:
# 		model = Seccion2026
# 		fields=['seccion','turno']
# 		widgets = {
# 			'seccion': forms.Select(
# 				attrs={'required': 'true'}),
# 				'turno': forms.Select(
# 				attrs={'required': 'true'})
# 				}
	
	
# class BorrarRegistroAlumnoForm(forms.Form):
# 		borrar= forms.BooleanField(label='borrar',required=False,
# 		widget=forms.RadioSelect(
# 			choices=[
# 				(True,'Eliminar registro'), 
# 				(False, 'NO eliminar registro ')
# 			]
# 		)
# 	)
# #----------------------VISUALIZACION---------------------
# # class DirectorForm(forms.Form):
# # 		SECTORES = [
# # 		('', '-------'),
# # 		('TODOS', '---TODOS LOS SECTORES----'),
# # 		('Estatal', 'Estatal'),
# # 		('Gestión social/cooperativa','Gestión social/cooperativa'),
# # 		('Privado', 'Privado'),
# # 		]
# # 		AMBITOS = [
# # 		('', '-------'),
# # 		('TODOS', '---TODOS LOS ÁMBITOS----'),
# # 		('Rural Aglomerado', 'Rural Aglomerado'),
# # 		('Rural Disperso', 'Rural Disperso'),
# # 		('Urbano', 'Urbano'),
# # 		]
	
# # 		sector = forms.ChoiceField(
# # 			choices=SECTORES, 
# # 			label="Sector de Gestión",
# # 			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
# # 		)
# # 		ambito= forms.ChoiceField(
# # 			choices=AMBITOS, 
# # 			label="Ámbito",
# # 			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
# # 		)

# # class DirectorNivelForm(DirectorForm):
# # 		REGIONES = [
# # 		('', '-------'),
# # 		('TODOS', '---TODAS LAS REGIONES----'),
# # 		('R.E. 1', 'R.E. 1'),
# # 		('SUB. R.E. 1-A', 'SUB. R.E. 1-A'),
# # 		('SUB. R.E. 1-B', 'SUB. R.E. 1-B'),
# # 		('R.E. 2', 'R.E. 2'),
# # 		('SUB. R.E. 2', 'SUB. R.E. 2'),
# # 		('R.E. 3', 'R.E. 3'),
# # 		('SUB. R.E. 3', 'SUB. R.E. 3'),
# # 		('R.E. 4-A', 'R.E. 4-A'),
# # 		('R.E. 4-B', 'R.E. 4-B'),
# # 		('R.E. 5', 'R.E. 5'),
# # 		('SUB. R.E. 5', 'SUB. R.E. 5'),
# # 		('R.E. 6', 'R.E. 6'),
# # 		('R.E. 7', 'R.E. 7'),
# # 		('R.E. 8-A', 'R.E. 8-A'),
# # 		('R.E. 8-B', 'R.E. 8-B'),
# # 		('R.E. 9', 'R.E. 9'),
# # 		('R.E. 10-A', 'R.E. 10-A'),
# # 		('R.E. 10-B', 'R.E. 10-B'),
# # 		('R.E. 10-C', 'R.E. 10-C'),	
# # 		]
		
# # 		region = forms.ChoiceField(
# # 			choices=REGIONES, 
# # 			label="Región",
# # 			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
# # 		)
	
# # class DirectorRegionalForm(DirectorForm):
# # 	NIVELES_EDUCATIVOS = [
# # 			('Rural Aglomerado', 'Rural Aglomerado'),
# # 			('Rural Disperso', 'Rural Disperso'),
# # 			('Urbano', 'Urbano'),
# # 		]
# # 	nivel_educativo= forms.ChoiceField(
# # 			choices=NIVELES_EDUCATIVOS, 
# # 			label="Nivel Educativo",
# # 			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
# # 		)
# # class DirectorGeneralForm(DirectorNivelForm,DirectorRegionalForm):
# # 	pass

# # class CueanexoForm(forms.Form):
# # 	# Usamos ChoiceField normal para permitir el valor "TODOS"
# # 	cueanexo_seleccionado = forms.ChoiceField(
# # 		label="Seleccione para procesar",
# # 		required=True,
# # 		choices=[('', '--- Seleccionar ---')], # Placeholder inicial
# # 		widget=forms.Select(attrs={'class': 'select2-buscable', 'id': 'id_cueanexo_seleccionado'})
# # 	)

# # 	def __init__(self, *args, **kwargs):
# # 		# Extraemos el CUIL de los argumentos
# # 		cuil = kwargs.pop('cuil', None)
# # 		nivel_acceso = kwargs.pop('nivel_acceso', None)
# # 		sector = kwargs.pop('sector', None)
# # 		ambito = kwargs.pop('ambito', None)
# # 		region = kwargs.pop('region', None)
# # 		super().__init__(*args, **kwargs)
		
# # 		if cuil:
# # 			cueanexo_grado= Grado.objects.values_list('cueanexo',flat=True).order_by('cueanexo')
# # 			lista_enteros = [int(i) for i in cueanexo_grado]

# # 			#print(f'consulta a grado{cueanexo_grado}')
# # 			if nivel_acceso == 'Director/a':
# # 				cuil_con_caracter = f"{cuil[:2]}-{cuil[2:10]}-{cuil[10:]}"
# # 				qs = CapaUnicaOfertas.objects.filter(
# # 					resploc_cuitcuil=cuil_con_caracter, oferta='Común - Primaria de 7 años ', cueanexo__in=lista_enteros
# # 				).only('cueanexo','nom_est')
# # 				choices = [('', '--------')]
# # 			elif nivel_acceso =='Regional':
# # 				region_regional = obtener_regional(cuil)
# # 				cueanexos=obtener_sector_ambito(sector,ambito)
# # 				cueanexo_grado= Grado.objects.filter(cueanexo__in=cueanexos).values_list('cueanexo',flat=True).order_by('cueanexo')
# # 				lista_enteros = [int(i) for i in cueanexo_grado]
# # 				#print(lista_enteros)
# # 				#print(f'listade cuenexos en regional{cueanexo_grado}')
# # 				# 1. Traemos solo los campos necesarios (optimización)
# # 				# nombres_campos = [f.name for f in CapaUnicaOfertas._meta.get_fields()]

# # 				# print(nombres_campos)
# # 				qs = CapaUnicaOfertas.objects.filter(
# # 					region_loc__in = region_regional, oferta='Común - Primaria de 7 años ', cueanexo__in=lista_enteros
# # 				).only('cueanexo','nom_est')
# # 				#print(f'regional lista{qs}')
# # 				choices = [
# # 					('', '--------'),
# # 					('TODOS', '----TODOS LOS CUEANEXOS----'),
# # 					]
# # 			else:
# # 				#region = obtener_regional(cuil)
# # 				cueanexos=obtener_sector_ambito_region(sector,ambito,region)
# # 				#print(region)
# # 				cueanexo_grado= Grado.objects.filter(cueanexo__in=cueanexos).values_list('cueanexo',flat=True).order_by('cueanexo')
# # 				lista_enteros = [int(i) for i in cueanexo_grado]
# # 				#print(lista_enteros)
# # 				#print(f'listade cuenexos en ministro{cueanexo_grado}')
# # 				# 1. Traemos solo los campos necesarios (optimización)
# # 				# nombres_campos = [f.name for f in CapaUnicaOfertas._meta.get_fields()]

# # 				#print(f'region que llega{region}')
# # 				#print(f'ambito que llega{ambito}')
# # 				#print(f'sector que llega{sector}')
# # 				if region=='TODOS':
# # 					qs = CapaUnicaOfertas.objects.filter(
# # 					 oferta='Común - Primaria de 7 años ', cueanexo__in=lista_enteros
# # 				).only('cueanexo','nom_est')
# # 				else:
# # 					qs = CapaUnicaOfertas.objects.filter(
# # 						region_loc = region, oferta='Común - Primaria de 7 años ', cueanexo__in=lista_enteros
# # 					).only('cueanexo','nom_est')
# # 				#print(f'ministro lista{qs}')
# # 				choices = [
# # 					('', '--------'),
# # 					('TODOS', '----TODOS LOS CUEANEXOS----'),
# # 					]
				
# # 			#lista_cueanexos_validos=[]
# # 			#print(f'QS{qs}')
# # 			for i in qs:
# # 				#lista_cueanexos_validos.append(i.cueanexo)
# # 				label = f'{i.nom_est}-({i.cueanexo})'
# # 				choices.append((i.cueanexo, label))

# # 			#cueanexo_grado= Grado.objects.filter(cueanexo__in=lista_cueanexos_validos).order_by('cueanexo')
# # 			#print(cueanexo_grado)
# # 			# 2. Armamos la lista de opciones manualmente
# # 			# choices = [('TODOS', '--- Todos los Cueanexos ---')]
# # 			#choices = [('', '--------')]
# # 			# 3. Iteramos sobre el queryset
# # 			# var=False
# # 			# for obj in cueanexo_grado:
# # 			# 	# Aquí puedes aplicar tu lógica de etiquetas
# # 			# 	if var==False or var!=obj.cueanexo:
# # 			# 		label = f"Cueanexo: {obj.cueanexo}"
# # 			# 		choices.append((obj.cueanexo, label))
# # 			# 		var=obj.cueanexo
# # 			# label = f"Cueanexo: {obj.cueanexo}"
# # 			# choices.append((obj.cueanexo, label))
# # 			#var=obj.cueanexo

# # 			# 4. Asignamos la lista final al campo
# # 			self.fields['cueanexo_seleccionado'].choices = choices

# # 			#ENTENDER ESTE CODIGO Y POR QUE NO FUNCION EL NUESTRO
# # class Grado_select_Form(forms.Form):
# # 	GRADOS_CHOICES = [
# # 		('', '--- Seleccionar Grado ---'),  # Valor vacío para la opción neutra
# # 		('2do Año/Grado', '2do Año/Grado'),
# # 		('3er Año/Grado', '3er Año/Grado'),
# # 	]
	
# # 	grado_seleccion = forms.ChoiceField(
# # 		choices=GRADOS_CHOICES,
# # 		label="Seleccione un Grado",
# # 		required=True,
# # 		widget=forms.Select()
# # 	)
# # class SeccionTurnoForm(forms.Form):
# # 	# Definimos el campo vacío inicialmente
# # 	seleccion = forms.ModelChoiceField(
# # 		queryset=Seccion.objects.none(), 
# # 		label="Seleccione para procesar",
# # 		required=True
# # 	)

# # 	def __init__(self, *args, **kwargs):
# # 		# 1. Extraemos 'grados' de los argumentos (y lo quitamos para no romper el super)
# # 		grados = kwargs.pop('grados', None)
# # 		super().__init__(*args, **kwargs)
		
# # 		# 2. Si recibimos grados, actualizamos el queryset del campo
# # 		if grados:
# # 			#print(grados)
# # 			qs = Seccion.objects.filter(grado_id__in=grados).only('id', 'seccion', 'turno')
# # 			#qs = Seccion.objects.filter(grado_id=grados).only('id', 'seccion', 'turno')
# # 			self.fields['seleccion'].queryset = qs
# # 			# Sobreescribimos la función de visualización sobre la marcha
# # 			self.fields['seleccion'].label_from_instance = lambda obj: f"Sección: {obj.seccion} - Turno: {obj.turno}"
# # 			# --- AQUÍ AGREGAMOS LA OPCIÓN EXTRA ---
# # 			# Convertimos el queryset a una lista de opciones y le sumamos la nuestra
# # 			choices = [('TODOS', '--- Todas las Secciones ---')] 

# # 			# Sumamos las opciones que vienen de la base de datos
# # 			choices.extend([
# # 				(obj.id, self.fields['seleccion'].label_from_instance(obj)) 
# # 				for obj in qs
# # 			])

# # 			# Le decimos al campo que use esta nueva lista mixta
# # 			self.fields['seleccion'].choices = choices

# # class CueanexoManualForm(forms.Form):
# # 	# Usamos ChoiceField porque no hay modelo vinculado
# # 	cueanexo_seleccionado = forms.ChoiceField(
# # 		label="Seleccione para procesar",
# # 		required=True,
# # 		widget=forms.Select(attrs={'class': 'form-control'})
# # 	)

# # 	def __init__(self, *args, **kwargs):
# # 		# 1. Extraemos 'opciones' que pasaremos desde la view
# # 		opciones_raw = kwargs.pop('opciones', [])
# # 		super().__init__(*args, **kwargs)
		
# # 		# 2. Construimos la lista de opciones (tupla: valor, etiqueta)
# # 		# Empezamos con la opción por defecto
# # 		choices = [('', '------')]

# # 		# 3. Agregamos lo que viene de la view (asumiendo que viene de un cursor de psycopg)
# # 		for opt in opciones_raw:
# # 			# Creamos una etiqueta bonita: "Sección: A"
# # 			label = f"Cueanexo: {opt['cueanexo']}"
# # 			# El valor será el ID o lo que necesites para el filtro SQL
# # 			value = opt['cueanexo']
# # 			choices.append((value, label))

# # 		# 4. Asignamos la lista al campo
# # 		self.fields['cueanexo_seleccionado'].choices = choices

# # class GradoManualForm(forms.Form):
# # # Usamos ChoiceField porque no hay modelo vinculado
# # 	GRADOS = [
# # 		('', '--- Seleccionar Grado ---'),
# # 		('Segundo', '2do Año/Grado'),
# # 		('Tercero', '3er Año/Grado'),
# # 		]
		
# # 	grado_seleccion = forms.ChoiceField(
# # 		choices=GRADOS, 
# # 		label="Grado",
# # 		widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
# # 	)

# # class SeccionTurnoManualForm(forms.Form):
# # 	# Usamos ChoiceField porque no hay modelo vinculado
# # 	seleccion = forms.ChoiceField(
# # 		label="Seleccione para procesar",
# # 		required=True,
# # 		widget=forms.Select(attrs={'class': 'form-control'})
# # 	)

# # 	def __init__(self, *args, **kwargs):
# # 		# 1. Extraemos 'opciones' que pasaremos desde la view
# # 		opciones_raw = kwargs.pop('opciones', [])
# # 		super().__init__(*args, **kwargs)
		
# # 		# 2. Construimos la lista de opciones (tupla: valor, etiqueta)
# # 		# Empezamos con la opción por defecto
# # 		choices = [('TODOS', '--- Todas las Secciones ---')]

# # 		# 3. Agregamos lo que viene de la view (asumiendo que viene de un cursor de psycopg)
# # 		for opt in opciones_raw:
# # 			# Creamos una etiqueta bonita: "Sección: A"
# # 			label = f"Sección: {opt['division']}"
# # 			# El valor será el ID o lo que necesites para el filtro SQL
# # 			value = opt['division']
# # 			choices.append((value, label))

# # 		# 4. Asignamos la lista al campo
# # 		self.fields['seleccion'].choices = choices

# # #----------------------FUNCIONES-------------------------------------------------------------
# # def conexion_bd():
# # 	db_params = {
# # 			"host": os.getenv('POSTGRES_HOST'),
# # 			"database": os.getenv('POSTGRES_DB'),
# # 			"user": os.getenv('POSTGRES_USER'),
# # 			"password": os.getenv('POSTGRES_PASSWORD'),
# # 			"port": os.getenv('POSTGRES_PORT'),
# # 		}
# # 	return db_params

# # def obtener_regional(cuil):
# # 	db_params = conexion_bd()
# # 	conn = None
# # 	regional= None

# # 	 #consutla a select * from public.usuarios_regionalusuarios where usuario=cuil_con_caracter
# # 	try:
# # 		# 1. Establecer la conexión
# # 		#ERROR AQUI
# # 		conn = psycopg2.connect(**db_params)
		
# # 		# 2. Crear el cursor (usamos RealDictCursor para traer nombres de columnas)
# # 		with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
# # 			if cuil:
# # 				cuil_string=f'{cuil}'
# # 				#print(cuil_string)
# # 				query_regiones=f"""
# # 						SELECT region_loc
# # 						FROM public.usuarios_regionalusuarios
# # 						WHERE usuario = %s
# # 						"""
# # 				cur.execute(query_regiones,(cuil_string,))
# # 				regional_datos = cur.fetchall()
# # 				regional=[]
# # 				for fila in regional_datos:
# # 					#print(fila['region_loc'])
# # 					regional.append(fila['region_loc'])
# # 	except (Exception, psycopg2.DatabaseError) as error:
# # 	# 5. Manejo de errores
# # 		print(f"Error al conectar o consultar: {error}")

# # 	finally:
# # 		# 6. Cerrar la conexión pase lo que pase
# # 		if conn is not None:
# # 			conn.close()
# # 			print("Conexión cerrada.") 
# # 	#print(regional)
# # 	return regional


# # def obtener_sector_ambito_region(sector, ambito, region):
# # 	db_params = conexion_bd()
# # 	conn = None
# # 	cueanexos = []
# # 	#print(f'{sector},{ambito},{region}')
# # 	# 1. Limpieza total de los parámetros que llegan del form
# # 	s = sector.strip() if (sector and str(sector).strip()) else None
# # 	a = ambito.strip() if (ambito and str(ambito).strip()) else None
# # 	r = region.strip() if (region and str(region).strip()) else None
	
# # 	# Filtro base obligatorio para tu reporte
# # 	oferta_val = '%Común - Primaria de 7 años%'

# # 	try:
# # 		conn = psycopg2.connect(**db_params)
# # 		with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
# # 			query_base = "SELECT cueanexo FROM v_capa_unica_ofertas"
			
# # 			# 2. EMPEZAMOS LA LISTA DINÁMICA
# # 			# Siempre incluimos la oferta como primer filtro
# # 			condiciones = ["oferta ILIKE %s"]
# # 			parametros = [oferta_val]

# # 			# Si el usuario eligió SECTOR, lo sumamos a la bolsa
# # 			if s and s!='TODOS':
# # 				condiciones.append("TRIM(sector) ILIKE %s")
# # 				parametros.append(s)
			
# # 			# Si el usuario eligió ÁMBITO, lo sumamos (usamos % para los Aglomerados/Dispersos)
# # 			if a and a!='TODOS':
# # 				condiciones.append("TRIM(ambito) ILIKE %s")
# # 				parametros.append(f"{a}%")
				
# # 			# Si el usuario eligió REGIÓN, la sumamos
# # 			if r and r!='TODOS':
# # 				condiciones.append("TRIM(region_loc) ILIKE %s")
# # 				parametros.append(r)

# # 			# 3. ARMADO FINAL DE LA QUERY
# # 			# Join une la lista con " AND ". Si hay 1 filtro, no pone AND. 
# # 			# Si hay 4, pone AND entre cada uno automáticamente.
# # 			query_final = f"{query_base} WHERE {' AND '.join(condiciones)}"

# # 			#print(f"DEBUG SQL: {query_final}")
# # 			#print(f"DEBUG PARAMS: {parametros}")

# # 			cur.execute(query_final, parametros)
# # 			cueanexos_bd = cur.fetchall()
# # 			cueanexos = [fila['cueanexo'] for fila in cueanexos_bd]
# # 			#print(cueanexos)
			
# # 	except Exception as error:
# # 		print(f"Error en la consulta: {error}")
# # 	finally:
# # 		if conn: conn.close()

# # 	return cueanexos

# # def obtener_sector_ambito(sector, ambito):
# #     db_params = conexion_bd()
# #     conn = None
# #     cueanexos = []
    
# #     # 1. Limpieza de parámetros
# #     s = sector.strip() if (sector and str(sector).strip()) else None
# #     a = ambito.strip() if (ambito and str(ambito).strip()) else None
    
# #     # Filtro base obligatorio
# #     oferta_val = '%Común - Primaria de 7 años%'

# #     try:
# #         conn = psycopg2.connect(**db_params)
# #         with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
# #             query_base = "SELECT cueanexo FROM v_capa_unica_ofertas"
            
# #             # 2. Construcción dinámica de condiciones (Sin Región)
# #             condiciones = ["oferta ILIKE %s"]
# #             parametros = [oferta_val]

# #             if s and s!='TODOS':
# #                 condiciones.append("TRIM(sector) ILIKE %s")
# #                 parametros.append(s)
            
# #             if a and a!='TODOS':
# #                 # Se mantiene el % para capturar variantes de Ámbito (Urbano/Rural)
# #                 condiciones.append("TRIM(ambito) ILIKE %s")
# #                 parametros.append(f"{a}%")

# # 			# 3. Armado final de la Query
# #             query_final = f"{query_base} WHERE {' AND '.join(condiciones)}"

# #             # Debug para control en consola
# #             #print(f"DEBUG SQL: {query_final}")
# #             #print(f"DEBUG PARAMS: {parametros}")

# #             cur.execute(query_final, parametros)
# #             cueanexos_bd = cur.fetchall()
# #             cueanexos = [fila['cueanexo'] for fila in cueanexos_bd]
            
# #     except Exception as error:
# #         print(f"Error en la consulta: {error}")
# #     finally:
# #         if conn: conn.close()

# #     return cueanexos
# #-----------------------------------------------------------------------------------