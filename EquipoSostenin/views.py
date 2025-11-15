from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponse
from .forms import BoletaForm
from .procesador import procesar_boleta
from django.contrib.auth.decorators import login_required
from .models import Boleta
import json
from django.contrib import messages

@login_required
def home_view(request):
    # En tu archivo views.py
    from django.shortcuts import render
    from django.contrib.auth.decorators import login_required
    from django.http import HttpResponse # Ya no la necesitamos

@login_required
def home_view(request):
    
    # 1. Creamos el diccionario de contexto con las variables que queremos pasar
    contexto = {
        'username': request.user.username,
        'first_name': request.user.first_name,
        # Puedes añadir más variables aquí si las necesitas
    }
    
    # 2. Usamos render() para combinar el contexto con la plantilla hub.html
    # Django buscará 'hub.html' en las carpetas 'templates' de tus apps.
    return render(request, 'home.html', contexto)

@login_required
def subir_boleta_view(request):
    if request.method == 'POST':
        form = BoletaForm(request.POST, request.FILES)

        if form.is_valid():
            nueva_boleta=form.save(commit=False)
            nueva_boleta.usuario=request.user
            nueva_boleta.estado_procesamiento='PENDIENTE'
            nueva_boleta.save()
            procesar_boleta(nueva_boleta.id)
            return redirect('home')
    else:
        form = BoletaForm()
    return render(request, 'subir_boleta.html', {'form': form})

@login_required
def dashboard_view(request):
    boletas_procesadas = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='PROCESADO'
    ).order_by('-fecha_emision') # El '-' significa descendente
    
    # También podemos obtener las boletas que fallaron, para avisarle
    boletas_error = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='ERROR'
    ).order_by('-fecha_registro')

    boletas_luz = boletas_procesadas.filter(servicio='Luz').order_by('fecha_emision')
    boletas_agua = boletas_procesadas.filter(servicio='Agua').order_by('fecha_emision')
    
    chart_luz_labels = json.dumps([b.fecha_emision.isoformat() for b in boletas_luz])
    chart_luz_data_monto = json.dumps([b.monto for b in boletas_luz])
    chart_luz_data_consumo = json.dumps([float(b.consumo) for b in boletas_luz])

    chart_agua_labels = json.dumps([b.fecha_emision.isoformat() for b in boletas_agua])
    chart_agua_data_monto = json.dumps([b.monto for b in boletas_agua])
    chart_agua_data_consumo = json.dumps([float(b.consumo) for b in boletas_agua])

    context = {
        'boletas_ok': boletas_procesadas,
        'boletas_error': boletas_error,
        'nombre_usuario': request.user.username,
        'chart_luz_labels':chart_luz_labels,
        'chart_luz_data_monto': chart_luz_data_monto,
        'chart_luz_data_consumo': chart_luz_data_consumo,
        'boletas_luz_existen': boletas_luz.exists(), 
        'chart_agua_labels': chart_agua_labels,
        'chart_agua_data_monto': chart_agua_data_monto,
        'chart_agua_data_consumo': chart_agua_data_consumo,
        'boletas_agua_existen': boletas_agua.exists(),
    }
    return render(request, 'dashboard.html', context)
        
    # 3. Pasamos los datos a la plantilla
    context = {
        'boletas_ok': boletas_procesadas,
        'boletas_error': boletas_error,
        'nombre_usuario': request.user.username,
    }
    
    # 4. Renderizamos la nueva plantilla (que crearemos a continuación)
    return render(request, 'EquipoSostenin/dashboard.html', context)

@login_required
def delete_boleta_view(request, boleta_id):
    boleta = get_object_or_404(Boleta, id=boleta_id)
    if boleta.usuario == request.user and request.method == 'POST':
        fecha_boleta = boleta.fecha_emision.strftime('%d-%m-%Y')
        boleta.delete()
        messages.success(request, f"Boleta del {fecha_boleta} eliminada correctamente.")

    elif boleta.usuario != request.user:
        messages.error(request, "No tienes permiso para eliminar esta boleta.")
    else:
        messages.error(request, "Error: Esta acción solo se puede realizar con un método POST.")
    return redirect('dashboard')
