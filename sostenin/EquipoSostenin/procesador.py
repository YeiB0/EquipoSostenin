# En sostenin/EquipoSostenin/pdf_processor.py

from .models import Boleta
import tabula
import pandas as pd
import re 
import pdfplumber 
from decimal import Decimal

MESES_MAP = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}

def procesar_boleta(boleta_id):
    """
    Procesa la boleta, extrayendo datos con Tabula (para tablas)
    y PdfPlumber (para texto plano).
    """
    print(f"Iniciando procesamiento para Boleta ID: {boleta_id}")
    boleta = None 

    try:
        boleta = Boleta.objects.get(id=boleta_id)
        ruta_archivo = boleta.archivo_boleta.path 
        
        print("Paso 1.A: Leyendo texto con PdfPlumber...")
        pdf_texto_plano = ""
        with pdfplumber.open(ruta_archivo) as pdf:
            pagina = pdf.pages[0]
            pdf_texto_plano = pagina.extract_text()
        
        if not pdf_texto_plano:
            raise Exception("PdfPlumber no pudo extraer texto del PDF.")
        
        print(f"Paso 2: Leyendo tablas PDF '{ruta_archivo}' con Tabula...")
        lista_dfs_crudos = tabula.read_pdf(
            ruta_archivo, 
            pages=1, 
            stream=True, 
            pandas_options={'header': None}
        )

        if not lista_dfs_crudos:
            raise Exception("Tabula no encontró la tabla de totales en el PDF.")
            
        print("¡ÉXITO! Tabula encontró 1 tabla (Totales).")
        
        datos_tabla_cruda = lista_dfs_crudos[0] 
        df_limpio = pd.DataFrame(datos_tabla_cruda)
        
        print("Paso 3: Limpiando datos de la tabla (Pandas)...")
        nuevos_nombres_columnas = [
            'Monto Exento', 'Monto Afecto', 'I.V.A.',
            'Total Mes', 'Saldo Anterior', 'Otros Cargos/Abonos',
            'Total a Pagar'
        ]
        df_limpio.columns = nuevos_nombres_columnas
        df_limpio = df_limpio.transpose().reset_index()
        df_limpio.columns = ['Concepto', 'Valor ($)']
        
        print("\n--- DATOS LIMPIOS (procesados por Pandas) ---")
        print(df_limpio)

        print("\nPaso 4: Extrayendo valores específicos...")
        
        # --- 4.1 Extraer "Monto" ---
        valor_total_raw = df_limpio.loc[df_limpio['Concepto'] == 'Total a Pagar']['Valor ($)'].iloc[0]
        if isinstance(valor_total_raw, bytes):
            valor_total_str = valor_total_raw.decode('utf-8')
        else:
            valor_total_str = str(valor_total_raw)
        
        monto_extraido = int(re.sub(r'[^\d]', '', valor_total_str))
        print(f"-> Monto Extraído: {monto_extraido}")

        # --- 4.2 Extraer "Consumo" (¡VERSIÓN CORREGIDA!) ---
        #
        # \s*kWh  -> Busca "cero o más espacios" antes de kWh (cubre "kWh" y " kWh")
        # re.IGNORECASE -> Ignora si es "Electricidad" o "electricidad"
        #
        match_consumo = re.search(
            r"Electricidad\s+consumida\s+([\d\.]+)\s*kWh", 
            pdf_texto_plano, 
            re.IGNORECASE
        )
        if not match_consumo:
            raise Exception("No se pudo encontrar 'Electricidad consumida' en el PDF.")
        
        consumo_str = match_consumo.group(1)
        consumo_limpio = re.sub(r'[^\d]', '', consumo_str)
        consumo_extraido = Decimal(consumo_limpio) 
        print(f"-> Consumo Extraído: {consumo_extraido} kWh")

        # --- 4.3 Extraer "Fecha Emisión" ---
        match_fecha = re.search(r"FECHA\s+EMISIÓN:\s*(\d{2})\s+([a-z]{3})\s+(\d{4})", pdf_texto_plano, re.IGNORECASE)
        if not match_fecha:
            raise Exception("No se pudo encontrar 'FECHA EMISIÓN' en el PDF.")
            
        dia_str, mes_str, ano_str = match_fecha.groups()
        mes_num = MESES_MAP.get(mes_str.lower())
        if not mes_num:
            raise Exception(f"Mes desconocido: '{mes_str}'")
            
        fecha_extraida = f"{ano_str}-{mes_num:02d}-{dia_str}"
        print(f"-> Fecha Extraída: {fecha_extraida}")

        # --- PASO 5: Actualizar la Base de Datos ---
        print("\nPaso 5: Guardando en la Base de Datos...")
        boleta.monto = monto_extraido
        boleta.consumo = consumo_extraido     
        boleta.fecha_emision = fecha_extraida 
        boleta.estado_procesamiento = 'PROCESADO'
        boleta.save()
        
        print(f"¡LISTO! Boleta ID: {boleta_id} procesada exitosamente.")

    except Exception as e:
        print(f"\n¡ERROR! Procesando Boleta ID: {boleta_id}. Error: {e}")
        if boleta:
            boleta.estado_procesamiento = 'ERROR'
            boleta.save()