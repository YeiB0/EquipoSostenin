from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponse
from .forms import BoletaForm
from .procesador import procesar_boleta
from django.contrib.auth.decorators import login_required
from .models import Boleta

def home_view(request):
    html = (
        "<h1>Bienvenido a Sostenin</h1>"
        "<p><a href='/admin/login/'>Iniciar Sesión (Admin)</a></p>"
        "<p><a href='/subir/'>Subir nueva boleta (requiere login)</a></p>"
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
    """
    Muestra al usuario todas sus boletas procesadas.
    """
    # 1. Filtramos las boletas por el usuario que ha iniciado sesión
    # 2. Filtramos solo las que están 'PROCESADO' (no 'PENDIENTE' o 'ERROR')
    # 3. Las ordenamos por fecha (de más nueva a más antigua)
    boletas_procesadas = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='PROCESADO'
    ).order_by('-fecha_emision') # El '-' significa descendente
    
    # También podemos obtener las boletas que fallaron, para avisarle
    boletas_error = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='ERROR'
    ).order_by('-fecha_registro')
    
    # 3. Pasamos los datos a la plantilla
    context = {
        'boletas_ok': boletas_procesadas,
        'boletas_error': boletas_error,
        'nombre_usuario': request.user.username,
    }
    
    # 4. Renderizamos la nueva plantilla (que crearemos a continuación)
    return render(request, 'EquipoSostenin/dashboard.html', context)
