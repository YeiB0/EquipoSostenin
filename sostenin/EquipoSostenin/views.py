from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponse
from .forms import BoletaForm
from .procesador import procesar_boleta
from django.contrib.auth.decorators import login_required
from .models import Boleta
import json

@login_required
def home_view(request):
    # Como está protegido por @login_required, ya no necesitamos
    # el 'if request.user.is_authenticated'.
    
    # Este es el nuevo "Hub" para usuarios logueados
    html = (
        f"<h1>Bienvenido al Hub, {request.user.username}!</h1>"
        f"<p>Hola {request.user.first_name}, ¿Qué deseas hacer hoy?</p>"
        "<hr>"
        "<p><a href='/dashboard/' style='font-size: 1.2em;'>Ver mi Dashboard (Gráficos)</a></p>"
        "<p><a href='/subir/' style='font-size: 1.2em;'>Subir Nueva Boleta</a></p>"
        "<hr style='margin-top: 20px;'>" # Separador
        # Añadimos el link de logout que apunta a la URL que creamos
        "<p><a href='/account/logout/' style='font-size: 1em; color: gray;'>Cerrar Sesión</a></p>"
    )
    return HttpResponse(html)

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
    return render(request, 'EquipoSostenin/subir_boleta.html', {'form': form})

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
    return render(request, 'EquipoSostenin/dashboard.html', context)
        
    # 3. Pasamos los datos a la plantilla
    context = {
        'boletas_ok': boletas_procesadas,
        'boletas_error': boletas_error,
        'nombre_usuario': request.user.username,
    }
    
    # 4. Renderizamos la nueva plantilla (que crearemos a continuación)
    return render(request, 'EquipoSostenin/dashboard.html', context)
