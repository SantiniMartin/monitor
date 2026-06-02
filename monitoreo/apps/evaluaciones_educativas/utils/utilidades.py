from apps.consultasge.models import CapaUnicaOfertas

def obtener_cueanexo(name):
	cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
	nombreCuenexo = CapaUnicaOfertas.objects.filter(resploc_cuitcuil=cuil_con_caracter,oferta__icontains='Secundaria Completa req. 7 años').first()
	numeroCueanexo= nombreCuenexo.cueanexo
	print("CUE Anexo encontrado:", numeroCueanexo)
	return numeroCueanexo


def obtener_cueanexos(name):
	cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
	return list(
		CapaUnicaOfertas.objects
			.filter(resploc_cuitcuil=cuil_con_caracter, oferta__icontains='Secundaria Completa req. 7 años')
			.values_list('cueanexo', flat=True)
			.distinct()
			.order_by('cueanexo')
	)
