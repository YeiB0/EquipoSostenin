from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponse
from .forms import BoletaForm
from .procesador import procesar_boleta
from django.contrib.auth.decorators import login_required
from .models import Boleta
import json
from django.contrib import messages
from django.db.models import Avg
from decimal import Decimal

@login_required
def home_view(request):
    # En tu archivo views.py
    from django.shortcuts import render
    from django.contrib.auth.decorators import login_required
    from django.http import HttpResponse # Ya no la necesitamos

@login_required
def home_view(request):
    
    # 1. Creamos el diccionario de contexto con las variables que queremos pasar
    context = {
        'username': request.user.username,
        'first_name': request.user.first_name,
        # Puedes añadir más variables aquí si las necesitas
    }
    
    # 2. Usamos render() para combinar el contexto con la plantilla hub.html
    # Django buscará 'hub.html' en las carpetas 'templates' de tus apps.
    return render(request, 'EquipoSostenin/home.html', context)

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
            messages.success(request, "¡Boleta subida! La estamos procesando. Los datos aparecerán en tu panel en unos segundos.")
            return redirect('subir_boleta')
    else:
        form = BoletaForm()
    return render(request, 'EquipoSostenin/subir_boleta.html', {'form': form})

@login_required
def dashboard_view(request):
    """
    Muestra el panel con tablas, gráficos y la nueva
    sección de "Huella de Consumo".
    """
    
    # --- 1. Constantes de Promedio Nacional (Opción B) ---
    # (Basado en datos del Min. de Energía y la Asoc. de Empresas Sanitarias)
    PROMEDIO_NACIONAL_LUZ_KWH = Decimal(180.0)
    PROMEDIO_NACIONAL_AGUA_M3 = Decimal(16.7)

    # --- 2. Datos para las Tablas (Lógica existente) ---
    boletas_procesadas = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='PROCESADO'
    ).order_by('-fecha_emision')
    
    boletas_error = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='ERROR'
    ).order_by('-fecha_registro')
    
    # --- 3. Datos para los Gráficos (Lógica existente) ---
    boletas_luz = boletas_procesadas.filter(servicio='Luz').order_by('fecha_emision')
    boletas_agua = boletas_procesadas.filter(servicio='Agua').order_by('fecha_emision')

    chart_luz_labels = json.dumps([b.fecha_emision.isoformat() for b in boletas_luz])
    chart_luz_data_monto = json.dumps([b.monto for b in boletas_luz])
    chart_luz_data_consumo = json.dumps([float(b.consumo) for b in boletas_luz])
    
    chart_agua_labels = json.dumps([b.fecha_emision.isoformat() for b in boletas_agua])
    chart_agua_data_monto = json.dumps([b.monto for b in boletas_agua])
    chart_agua_data_consumo = json.dumps([float(b.consumo) for b in boletas_agua])

    # --- 4. INICIO: NUEVA LÓGICA DE "HUELLA DE CONSUMO" ---
    
    # 'context_huella' guardará todos nuestros nuevos cálculos
    context_huella = {} 

    # --- Cálculo para LUZ ---
    if boletas_luz.exists():
        # Obtenemos la última boleta de luz del usuario
        ultimo_consumo_luz = boletas_luz.last().consumo
        
        # Opción A: Promedio de todos los usuarios de la APP
        # Usamos Avg() de Django para pedirle la media a la BD
        promedio_app_luz_raw = Boleta.objects.filter(servicio='Luz').aggregate(Avg('consumo'))['consumo__avg']
        # Si no hay datos (None), lo dejamos en 0.0
        promedio_app_luz = promedio_app_luz_raw or Decimal(0.0)

        # Calculamos la "Huella" (el % de diferencia)
        # ([Consumo Usuario] / [Promedio]) - 1.0) * 100
        
        # vs. Nacional (Opción B)
        huella_luz_nacional = ((ultimo_consumo_luz / PROMEDIO_NACIONAL_LUZ_KWH) - 1) * 100
        
        # vs. App (Opción A)
        huella_luz_app = Decimal(0.0)
        if promedio_app_luz > 0:
            huella_luz_app = ((ultimo_consumo_luz / promedio_app_luz) - 1) * 100
        
        # Guardamos todo en el diccionario
        context_huella['luz'] = {
            'ultimo_consumo': ultimo_consumo_luz,
            'promedio_nacional': PROMEDIO_NACIONAL_LUZ_KWH,
            'promedio_app': promedio_app_luz,
            'huella_nacional_pct': huella_luz_nacional,
            'huella_app_pct': huella_luz_app,
        }

    # --- Cálculo para AGUA ---
    if boletas_agua.exists():
        ultimo_consumo_agua = boletas_agua.last().consumo
        
        # Opción A
        promedio_app_agua_raw = Boleta.objects.filter(servicio='Agua').aggregate(Avg('consumo'))['consumo__avg']
        promedio_app_agua = promedio_app_agua_raw or Decimal(0.0)

        # Opción B
        huella_agua_nacional = ((ultimo_consumo_agua / PROMEDIO_NACIONAL_AGUA_M3) - 1) * 100
        
        # Opción A
        huella_agua_app = Decimal(0.0)
        if promedio_app_agua > 0:
            huella_agua_app = ((ultimo_consumo_agua / promedio_app_agua) - 1) * 100
            
        context_huella['agua'] = {
            'ultimo_consumo': ultimo_consumo_agua,
            'promedio_nacional': PROMEDIO_NACIONAL_AGUA_M3,
            'promedio_app': promedio_app_agua,
            'huella_nacional_pct': huella_agua_nacional,
            'huella_app_pct': huella_agua_app,
        }

    # --- 5. Pasamos TODOS los datos al contexto ---
    context = {
        # Datos de Tablas
        'boletas_ok': boletas_procesadas,
        'boletas_error': boletas_error,
        'nombre_usuario': request.user.username,
        
        # Datos de Gráficos
        'chart_luz_labels': chart_luz_labels,
        'chart_luz_data_monto': chart_luz_data_monto,
        'chart_luz_data_consumo': chart_luz_data_consumo,
        'boletas_luz_existen': boletas_luz.exists(),
        
        'chart_agua_labels': chart_agua_labels,
        'chart_agua_data_monto': chart_agua_data_monto,
        'chart_agua_data_consumo': chart_agua_data_consumo,
        'boletas_agua_existen': boletas_agua.exists(),

        # ¡NUEVO! Datos de la Huella
        'huella': context_huella,
    }
    
    # Finalmente, renderizamos la plantilla pasándole todos los datos
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
