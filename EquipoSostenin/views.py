# En sostenin/EquipoSostenin/views.py

# --- (Asegúrate de que todas tus importaciones estén al inicio) ---
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import BoletaForm
from .procesador import procesar_boleta
from django.contrib.auth.decorators import login_required
from .models import Boleta 
import json
import random
from django.contrib import messages
from django.db.models import Avg
from decimal import Decimal

@login_required
def home_view(request):
    """
    Esta es tu vista de "Hub" principal.
    Ahora con lógica de "Huella Rápida" y "Tip del Día".
    """
    
    # --- Lógica de Huella (que ya tenías) ---
    PROMEDIO_NACIONAL_LUZ_KWH = Decimal(180.0)
    PROMEDIO_NACIONAL_AGUA_M3 = Decimal(16.7)
    huella_luz_snapshot = None
    huella_agua_snapshot = None

    ultima_boleta_luz = Boleta.objects.filter(
        usuario=request.user, estado_procesamiento='PROCESADO', servicio='Luz'
    ).order_by('-fecha_emision').first()

    if ultima_boleta_luz:
        huella_pct = ((ultima_boleta_luz.consumo / PROMEDIO_NACIONAL_LUZ_KWH) - 1) * 100
        huella_luz_snapshot = {
            'tipo': 'Luz', 'consumo': ultima_boleta_luz.consumo,
            'porcentaje': huella_pct, 'css_class': 'ranking-rojo' if huella_pct > 0 else 'ranking-verde'
        }

    ultima_boleta_agua = Boleta.objects.filter(
        usuario=request.user, estado_procesamiento='PROCESADO', servicio='Agua'
    ).order_by('-fecha_emision').first()

    if ultima_boleta_agua:
        huella_pct = ((ultima_boleta_agua.consumo / PROMEDIO_NACIONAL_AGUA_M3) - 1) * 100
        huella_agua_snapshot = {
            'tipo': 'Agua', 'consumo': ultima_boleta_agua.consumo,
            'porcentaje': huella_pct, 'css_class': 'ranking-rojo' if huella_pct > 0 else 'ranking-verde'
        }
    
    # --- ¡INICIO DE LA LÓGICA (TIP DEL DÍA)! ---
    lista_de_tips = [
        "💡 ¿Sabías que los cargadores enchufados (incluso sin un teléfono) siguen consumiendo energía? ¡Desconéctalos!",
        "💧 ¡Una ducha de 5 minutos ahorra más de 30 litros de agua en comparación con una de 10 minutos!",
        "💡 Apaga las luces al salir de una habitación. ¡Es el hábito de ahorro más simple y efectivo!",
        "💧 Cierra la llave mientras te lavas los dientes. Puedes ahorrar hasta 10 litros de agua cada vez.",
        "💡 Usa ampolletas LED. Consumen hasta un 80% menos de energía que las incandescentes.",
    ]
    tip_del_dia = random.choice(lista_de_tips)
    # --- FIN DE LA LÓGICA ---

    contexto = {
        'nombre_usuario': request.user.username,
        'nombre_real': request.user.first_name,
        'huella_luz_snapshot': huella_luz_snapshot,
        'huella_agua_snapshot': huella_agua_snapshot,
        'tip_del_dia': tip_del_dia, # <-- ¡Pasamos el tip al contexto!
    }
    
    return render(request, 'EquipoSostenin/home.html', contexto)

@login_required 
def subir_boleta_view(request):
    """
    Esta es tu vista para subir boletas.
    (Incluye la lógica para quedarse en la misma página)
    """
    if request.method == 'POST':
        form = BoletaForm(request.POST, request.FILES)
        
        if form.is_valid():
            nueva_boleta = form.save(commit=False)
            nueva_boleta.usuario = request.user 
            nueva_boleta.estado_procesamiento = 'PENDIENTE'
            nueva_boleta.save()
            
            # Llama a tu procesador de PDF
            # (¡Asegúrate de que 'procesar_boleta' esté importado al inicio del archivo!)
            procesar_boleta(nueva_boleta.id) 
            
            # 1. Creamos el mensaje de éxito
            messages.success(request, "¡Boleta subida! La estamos procesando. Los datos aparecerán en tu panel en unos segundos.")
            
            # 2. Redirigimos a la *misma* página ('subir_boleta')
            return redirect('subir_boleta') 

    else:
        form = BoletaForm()
        
    # Asegúrate de que tu plantilla se llame 'subir_boleta.html'
    return render(request, 'EquipoSostenin/subir_boleta.html', {'form': form})


@login_required
def delete_boleta_view(request, boleta_id):
    """
    Esta es tu vista para eliminar una boleta.
    """
    boleta = get_object_or_404(Boleta, id=boleta_id)
    
    if boleta.usuario == request.user and request.method == 'POST':
        fecha_boleta = boleta.fecha_emision.strftime('%d-%m-%Y')
        boleta.delete()
        messages.success(request, f"Boleta del {fecha_boleta} eliminada correctamente.")
    
    elif boleta.usuario != request.user:
        messages.error(request, "No tienes permiso para eliminar esta boleta.")
        
    else:
        messages.error(request, "Error: Esta acción solo se puede realizar con un método POST.")

    # Redirigimos al usuario de vuelta al dashboard
    return redirect('dashboard')
@login_required
def dashboard_view(request):
    """
    Muestra el panel con tablas, gráficos y la 
    "Huella de Consumo" (¡con Gamificación!).
    """
    
    # --- 1. Constantes de Promedio Nacional ---
    PROMEDIO_NACIONAL_LUZ_KWH = Decimal(180.0)
    PROMEDIO_NACIONAL_AGUA_M3 = Decimal(16.7)

    # --- 2. Datos para las Tablas ---
    boletas_procesadas = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='PROCESADO'
    ).order_by('-fecha_emision')
    
    boletas_error = Boleta.objects.filter(
        usuario=request.user,
        estado_procesamiento='ERROR'
    ).order_by('-fecha_registro')
    
    # --- 3. Datos para los Gráficos ---
    boletas_luz = boletas_procesadas.filter(servicio='Luz').order_by('fecha_emision')
    boletas_agua = boletas_procesadas.filter(servicio='Agua').order_by('fecha_emision')

    chart_luz_labels = json.dumps([b.fecha_emision.isoformat() for b in boletas_luz])
    chart_luz_data_monto = json.dumps([b.monto for b in boletas_luz])
    chart_luz_data_consumo = json.dumps([float(b.consumo) for b in boletas_luz])
    
    chart_agua_labels = json.dumps([b.fecha_emision.isoformat() for b in boletas_agua])
    chart_agua_data_monto = json.dumps([b.monto for b in boletas_agua])
    chart_agua_data_consumo = json.dumps([float(b.consumo) for b in boletas_agua])

    # --- 4. LÓGICA DE "HUELLA DE CONSUMO" Y "GAMIFICACIÓN" ---
    
    context_huella = {} 

    # --- Cálculo para LUZ ---
    if boletas_luz.exists():
        ultimo_consumo_luz = boletas_luz.last().consumo
        promedio_app_luz_raw = Boleta.objects.filter(servicio='Luz').aggregate(Avg('consumo'))['consumo__avg']
        promedio_app_luz = promedio_app_luz_raw or Decimal(0.0)
        huella_luz_nacional_pct = ((ultimo_consumo_luz / PROMEDIO_NACIONAL_LUZ_KWH) - 1) * 100
        
        huella_luz_app_pct = Decimal(0.0)
        if promedio_app_luz > 0:
            huella_luz_app_pct = ((ultimo_consumo_luz / promedio_app_luz) - 1) * 100
        
        # --- ¡INICIO DE LA LÓGICA DE GAMIFICACIÓN (LUZ)! ---
        ranking_luz = ""
        tip_luz = ""
        ranking_css_luz = "" # Clase CSS para el color

        if huella_luz_nacional_pct < -15:
            ranking_luz = "🌳 Súper Ahorrador"
            tip_luz = "¡Felicidades! Tu consumo es ejemplar y muy inferior al promedio nacional."
            ranking_css_luz = "ranking-verde"
        elif huella_luz_nacional_pct < 0:
            ranking_luz = "👍 Eco-Consciente"
            tip_luz = "¡Muy bien! Estás bajo el promedio nacional. Sigue así."
            ranking_css_luz = "ranking-verde"
        elif huella_luz_nacional_pct < 20:
            ranking_luz = "⚠️ Consumo Promedio"
            tip_luz = "Estás en el rango del promedio. Prueba desconectar aparatos que no uses."
            ranking_css_luz = "ranking-naranja"
        else:
            ranking_luz = "🚨 Consumo Elevado"
            tip_luz = "Tu consumo es significativamente alto. Revisa nuestros tips de ahorro."
            ranking_css_luz = "ranking-rojo"
        # --- FIN DE LA LÓGICA DE GAMIFICACIÓN (LUZ) ---
            
        context_huella['luz'] = {
            'ultimo_consumo': ultimo_consumo_luz,
            'promedio_nacional': PROMEDIO_NACIONAL_LUZ_KWH,
            'promedio_app': promedio_app_luz,
            'huella_nacional_pct': huella_luz_nacional_pct,
            'huella_app_pct': huella_luz_app_pct,
            'ranking': ranking_luz, # <-- Nuevo
            'tip': tip_luz,         # <-- Nuevo
            'css_class': ranking_css_luz, # <-- Nuevo
        }

    # --- Cálculo para AGUA ---
    if boletas_agua.exists():
        ultimo_consumo_agua = boletas_agua.last().consumo
        promedio_app_agua_raw = Boleta.objects.filter(servicio='Agua').aggregate(Avg('consumo'))['consumo__avg']
        promedio_app_agua = promedio_app_agua_raw or Decimal(0.0)
        huella_agua_nacional_pct = ((ultimo_consumo_agua / PROMEDIO_NACIONAL_AGUA_M3) - 1) * 100
        
        huella_agua_app_pct = Decimal(0.0)
        if promedio_app_agua > 0:
            huella_agua_app_pct = ((ultimo_consumo_agua / promedio_app_agua) - 1) * 100
            
        # --- ¡INICIO DE LA LÓGICA DE GAMIFICACIÓN (AGUA)! ---
        ranking_agua = ""
        tip_agua = ""
        ranking_css_agua = ""

        if huella_agua_nacional_pct < -15:
            ranking_agua = "🌊 Guardián del Agua"
            tip_agua = "¡Excelente! Tu consumo de agua es muy responsable."
            ranking_css_agua = "ranking-verde"
        elif huella_agua_nacional_pct < 0:
            ranking_agua = "👍 Eco-Consciente"
            tip_agua = "¡Bien hecho! Tu consumo está bajo el promedio nacional."
            ranking_css_agua = "ranking-verde"
        elif huella_agua_nacional_pct < 20:
            ranking_agua = "💧 Consumo Promedio"
            tip_agua = "Estás en el rango del promedio. ¡Intenta reducir las duchas!"
            ranking_css_agua = "ranking-naranja"
        else:
            ranking_agua = "🚨 Consumo Elevado"
            tip_agua = "Tu consumo de agua es alto. ¡Revisa si tienes fugas!"
            ranking_css_agua = "ranking-rojo"
        # --- FIN DE LA LÓGICA DE GAMIFICACIÓN (AGUA) ---

        context_huella['agua'] = {
            'ultimo_consumo': ultimo_consumo_agua,
            'promedio_nacional': PROMEDIO_NACIONAL_AGUA_M3,
            'promedio_app': promedio_app_agua,
            'huella_nacional_pct': huella_agua_nacional_pct,
            'huella_app_pct': huella_agua_app_pct,
            'ranking': ranking_agua, # <-- Nuevo
            'tip': tip_agua,         # <-- Nuevo
            'css_class': ranking_css_agua, # <-- Nuevo
        }

    # --- 5. Pasamos TODOS los datos al contexto ---
    context = {
        'boletas_ok': boletas_procesadas,
        'boletas_error': boletas_error,
        'nombre_usuario': request.user.username,
        'chart_luz_labels': chart_luz_labels,
        'chart_luz_data_monto': chart_luz_data_monto,
        'chart_luz_data_consumo': chart_luz_data_consumo,
        'boletas_luz_existen': boletas_luz.exists(),
        'chart_agua_labels': chart_agua_labels,
        'chart_agua_data_monto': chart_agua_data_monto,
        'chart_agua_data_consumo': chart_agua_data_consumo,
        'boletas_agua_existen': boletas_agua.exists(),
        'huella': context_huella,
    }
    
    return render(request, 'EquipoSostenin/dashboard.html', context)