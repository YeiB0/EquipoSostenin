# En sostenin/EquipoSostenin/procesador.py

from .models import Boleta
import tabula
import pandas as pd
import re 
import pdfplumber 
from decimal import Decimal

# (El MESES_MAP queda igual)
MESES_MAP = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}

# (La función _limpiar_monto() queda igual)
def _limpiar_monto(texto_numero):
    if isinstance(texto_numero, bytes):
        texto_numero = texto_numero.decode('utf-8')
    else:
        texto_numero = str(texto_numero)
    numero_limpio = re.sub(r'[^\d]', '', texto_numero)
    if not numero_limpio:
        return Decimal(0)
    return Decimal(numero_limpio)

# (La función _limpiar_consumo_decimal() queda igual)
def _limpiar_consumo_decimal(texto_numero):
    if isinstance(texto_numero, bytes):
        texto_numero = texto_numero.decode('utf-8')
    else:
        texto_numero = str(texto_numero)
    numero_limpio = texto_numero.replace('.', '').replace(',', '.')
    numero_limpio = re.sub(r'[^\d\.]', '', numero_limpio)
    if not numero_limpio:
        return Decimal(0)
    return Decimal(numero_limpio)

# (La función _procesar_chilquinta() queda igual)
def _procesar_chilquinta(boleta, pdf_texto_plano):
    print("-> Detectado: CHILQUINTA. Iniciando extractor de Chilquinta...")
    
    lista_dfs_crudos = tabula.read_pdf(
        boleta.archivo_boleta.path, pages=1, stream=True, pandas_options={'header': None}
    )
    if not lista_dfs_crudos:
        raise Exception("CHILQUINTA: Tabula no encontró la tabla de totales.")
        
    datos_tabla_cruda = lista_dfs_crudos[0] 
    df_limpio = pd.DataFrame(datos_tabla_cruda)
    
    nuevos_nombres_columnas = [
        'Monto Exento', 'Monto Afecto', 'I.V.A.',
        'Total Mes', 'Saldo Anterior', 'Otros Cargos/Abonos',
        'Total a Pagar'
    ]
    df_limpio.columns = nuevos_nombres_columnas
    df_limpio = df_limpio.transpose().reset_index()
    df_limpio.columns = ['Concepto', 'Valor ($)']
    
    valor_total_raw = df_limpio.loc[df_limpio['Concepto'] == 'Total a Pagar']['Valor ($)'].iloc[0]
    monto_extraido = _limpiar_monto(valor_total_raw)
    
    match_consumo = re.search(r"Electricidad\s+consumida\s+([\d\.]+)\s*kWh", pdf_texto_plano, re.IGNORECASE)
    if not match_consumo:
        raise Exception("CHILQUINTA: No se pudo encontrar 'Electricidad consumida' en el PDF.")
    
    consumo_extraido = _limpiar_monto(match_consumo.group(1))

    match_fecha = re.search(r"FECHA\s+EMISIÓN:\s*(\d{2})\s+([a-z]{3})\s+(\d{4})", pdf_texto_plano, re.IGNORECASE)
    if not match_fecha:
        raise Exception("CHILQUINTA: No se pudo encontrar 'FECHA EMISIÓN' en el PDF.")
        
    dia_str, mes_str, ano_str = match_fecha.groups()
    mes_num = MESES_MAP.get(mes_str.lower())
    if not mes_num:
        raise Exception(f"CHILQUINTA: Mes desconocido: '{mes_str}'")
        
    fecha_extraida = f"{ano_str}-{mes_num:02d}-{dia_str}"

    return monto_extraido, consumo_extraido, fecha_extraida

# (La función _procesar_cge() queda igual)
def _procesar_cge(boleta, pdf_texto_plano):
    print("-> Detectado: CGE. Iniciando extractor de CGE...")
    
    match_monto = re.search(r"Total a pagar\s+\$\s*([\d\.]+)", pdf_texto_plano, re.IGNORECASE)
    if not match_monto:
        raise Exception("CGE: No se pudo encontrar 'Total a pagar' en el PDF.")
    
    monto_extraido = _limpiar_monto(match_monto.group(1))

    match_consumo = re.search(r"Electricidad consumida \((\d+)\s*kWh\)", pdf_texto_plano, re.IGNORECASE)
    if not match_consumo:
        raise Exception("CGE: No se pudo encontrar 'Electricidad consumida (XXX kWh)' en el PDF.")
    
    consumo_extraido = _limpiar_monto(match_consumo.group(1))

    match_fecha = re.search(r"Fecha de emisión:\s*(\d{2})\s+([a-z]{3})\s+(\d{4})", pdf_texto_plano, re.IGNORECASE)
    if not match_fecha:
        raise Exception("CGE: No se pudo encontrar 'Fecha de emisión' en el PDF.")
        
    dia_str, mes_str, ano_str = match_fecha.groups()
    mes_num = MESES_MAP.get(mes_str.lower())
    if not mes_num:
        raise Exception(f"CGE: Mes desconocido: '{mes_str}'")
        
    fecha_extraida = f"{ano_str}-{mes_num:02d}-{dia_str}"

    return monto_extraido, consumo_extraido, fecha_extraida

# --- ¡FUNCIÓN _procesar_esval() (CORREGIDA!) ---
def _procesar_esval(boleta, pdf_texto_plano):
    """
    Lógica de extracción específica para boletas ESVAL.
    """
    print("-> Detectado: ESVAL. Iniciando extractor de Esval...")

    # --- 1. Extraer Monto (Total a pagar) ---
    match_monto = re.search(r"Monto Total\s+\$\s*([\d\.]+)", pdf_texto_plano, re.IGNORECASE)
    if not match_monto:
        match_monto = re.search(r"TOTAL A PAGAR\s+\$\s*([\d\.]+)", pdf_texto_plano, re.IGNORECASE)
        if not match_monto:
            raise Exception("ESVAL: No se pudo encontrar 'Monto Total' ni 'TOTAL A PAGAR' en el PDF.")
    
    monto_extraido = _limpiar_monto(match_monto.group(1))

    # --- 2. Extraer Consumo ---
    match_consumo = re.search(r"consumo agua\s+([\d\.,]+)m3", pdf_texto_plano, re.IGNORECASE)
    if not match_consumo:
        match_consumo = re.search(r"A Facturar\s+([\d\.,]+)m3", pdf_texto_plano, re.IGNORECASE)
        if not match_consumo:
            raise Exception("ESVAL: No se pudo encontrar 'consumo agua' ni 'A Facturar' en el PDF.")
    
    consumo_extraido = _limpiar_consumo_decimal(match_consumo.group(1))

    # --- 3. Extraer Fecha Emisión (¡VERSIÓN CORREGIDA!) ---
    # Buscamos: "Fecha Emisión" (opcionalmente ":") "03" (guión O slash) "01" (guión O slash) "2025"
    # [/-] significa "un guión o un slash"
    match_fecha = re.search(r"Fecha Emisión:?\s*(\d{2})[/-](\d{2})[/-](\d{4})", pdf_texto_plano, re.IGNORECASE)
    if not match_fecha:
        raise Exception("ESVAL: No se pudo encontrar 'Fecha Emisión' (con formato DD-MM-YYYY o DD/MM/YYYY) en el PDF.")
        
    dia_str, mes_str, ano_str = match_fecha.groups()
    
    fecha_extraida = f"{ano_str}-{mes_str}-{dia_str}"

    return monto_extraido, consumo_extraido, fecha_extraida


# --- FUNCIÓN "MAESTRA" (Queda igual que la v3.3) ---
def procesar_boleta(boleta_id):
    """
    Función "Maestra" que lee una boleta, detecta el proveedor
    y llama al extractor correspondiente.
    """
    print(f"Iniciando procesamiento para Boleta ID: {boleta_id}")
    boleta = None 

    try:
        boleta = Boleta.objects.get(id=boleta_id)
        ruta_archivo = boleta.archivo_boleta.path 
        
        print("Paso 1: Leyendo texto con PdfPlumber para detectar proveedor...")
        pdf_texto_plano = ""
        with pdfplumber.open(ruta_archivo) as pdf:
            if not pdf.pages:
                 raise Exception("El PDF está vacío o corrupto, no tiene páginas.")
            
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    pdf_texto_plano += texto_pagina + "\n"
        
        if not pdf_texto_plano:
            raise Exception("PdfPlumber no pudo extraer texto del PDF.")

        print("Paso 2: Detectando proveedor...")
        
        texto_lower = pdf_texto_plano.lower() 
        
        if "chilquinta" in texto_lower:
            monto, consumo, fecha = _procesar_chilquinta(boleta, pdf_texto_plano)
            
        elif "76.411.321" in texto_lower: # RUT de CGE (con puntos)
            monto, consumo, fecha = _procesar_cge(boleta, pdf_texto_plano)
            
        elif "oficinavirtual.esval.cl" in texto_lower: # URL de Esval
            monto, consumo, fecha = _procesar_esval(boleta, pdf_texto_plano)
            
        else:
            raise Exception("Proveedor de boleta no reconocido. No es CGE, Chilquinta ni Esval.")

        print("\nPaso 3: Guardando datos extraídos en la Base de Datos...")
        boleta.monto = monto
        boleta.consumo = consumo
        boleta.fecha_emision = fecha
        
        boleta.estado_procesamiento = 'PROCESADO'
        boleta.save()
        
        print(f"¡LISTO! Boleta ID: {boleta_id} procesada exitosamente.")

    except Exception as e:
        print(f"\n¡ERROR! Procesando Boleta ID: {boleta_id}. Error: {e}")
        if boleta:
            boleta.estado_procesamiento = 'ERROR'
            boleta.save()