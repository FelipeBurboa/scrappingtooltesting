import os
import json
import pandas as pd
from config.settings import DOWNLOADS_DIR


def parse_excel_to_json(excel_file_path, output_json_path=None, report_type=None):
    """
    Convierte el archivo Excel a formato JSON
    
    Args:
        excel_file_path (str): Ruta al archivo Excel
        output_json_path (str): Ruta donde guardar el archivo JSON (opcional)
        report_type (str): Tipo de reporte para formateo específico ('mermasventas', 'catalogados', 'stockdetalle')
    
    Returns:
        list: Lista de diccionarios con los datos del Excel
    """
    print(f"\nIniciando conversión de Excel a JSON...")
    print(f"Archivo Excel: {excel_file_path}")
    print(f"Tipo de reporte: {report_type}")
    
    try:
        # Define qué columnas deben mantenerse como string para preservar formato
        string_columns = {'Artículo': str}  # Preserva ceros iniciales en Artículo
        
        # Para Mermas y Ventas, también preserva Artículo ID como string con ceros
        if report_type == 'mermasventas':
            string_columns.update({
                'Artículo ID': str,  # Preserva ceros iniciales en Artículo ID
                'Artículo': str
            })
        
        # Lee el archivo Excel comenzando desde la fila 3 (índice 2) que contiene los headers
        print("Leyendo archivo Excel...")
        df = pd.read_excel(excel_file_path, header=2, dtype=string_columns)
        
        # Muestra información básica del DataFrame
        print(f"Número de filas: {len(df)}")
        print(f"Número de columnas: {len(df.columns)}")
        print(f"Columnas encontradas: {list(df.columns)}")
        
        # Limpia los nombres de las columnas (elimina espacios extra)
        df.columns = df.columns.str.strip()
        
        # Skip first row if it's exactly "Total" 
        if len(df) > 0:
            first_row = df.iloc[0]
            # Check if the first column (usually "Día") contains exactly "Total"
            first_value = str(first_row.iloc[0]).strip().lower() if len(first_row) > 0 else ""
            if first_value == 'total':
                print("🗑️ Skipping first row (Total row detected)")
                df = df.iloc[1:].reset_index(drop=True)
                print(f"Filas después de skip: {len(df)}")
        
        # Convierte el DataFrame a una lista de diccionarios
        print("Convirtiendo datos a formato JSON...")
        json_data = []
        
        for index, row in df.iterrows():
            # Crea un diccionario para cada fila
            row_dict = {
                "n": index + 1,  # Número de fila empezando desde 1
            }
            
            # Agrega cada columna al diccionario
            for column in df.columns:
                # Maneja valores NaN/None
                value = row[column]
                if pd.isna(value) or value == 'nan':
                    value = None
                elif column == 'Artículo':
                    # Para la columna Artículo, asegura que se mantenga como string
                    value = str(value).strip() if value is not None else None
                elif column == 'Artículo ID' and report_type == 'mermasventas':
                    # Para Mermas y Ventas: Artículo ID debe tener formato con ceros iniciales
                    if value is not None:
                        # Convierte a string y formatea con ceros iniciales (18 dígitos total)
                        try:
                            # Si es un número, lo convierte a entero primero para quitar decimales
                            if isinstance(value, (int, float)):
                                value = int(value)
                            # Formatea con ceros iniciales
                            value = f"{int(value):018d}"
                        except (ValueError, TypeError):
                            # Si no se puede convertir, mantiene como string limpio
                            value = str(value).strip()
                    else:
                        value = None
                elif isinstance(value, (int, float)) and pd.notna(value):
                    # Mantiene los números como están para otras columnas
                    value = value
                else:
                    # Convierte a string y limpia espacios para el resto
                    value = str(value).strip() if value is not None else None
                
                row_dict[column] = value
            
            json_data.append(row_dict)
        
        print(f"Conversión completada. Total de registros: {len(json_data)}")
        
        # Guarda el archivo JSON si se especifica una ruta
        if output_json_path:
            print(f"\nGuardando archivo JSON en: {output_json_path}")
            with open(output_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=2, default=str)
            print("Archivo JSON guardado exitosamente")
        
        return json_data
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo {excel_file_path}")
        return None
    except Exception as e:
        print(f"Error al procesar el archivo Excel: {e}")
        return None


def find_latest_catalogados_file():
    """
    Busca el archivo de catalogados más reciente en la carpeta downloads
    
    Returns:
        str: Ruta al archivo encontrado o None si no se encuentra
    """
    if not os.path.exists(DOWNLOADS_DIR):
        print(f"Error: La carpeta {DOWNLOADS_DIR} no existe")
        return None
    
    # Busca archivos que contengan "catalogados" en el nombre
    catalogados_files = []
    for filename in os.listdir(DOWNLOADS_DIR):
        if "catalogados" in filename.lower() and filename.endswith('.xlsx'):
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            catalogados_files.append((file_path, os.path.getmtime(file_path)))
    
    if not catalogados_files:
        print("No se encontraron archivos de catalogados en la carpeta downloads")
        return None
    
    # Retorna el archivo más reciente
    latest_file = max(catalogados_files, key=lambda x: x[1])[0]
    print(f"Archivo de catalogados encontrado: {latest_file}")
    return latest_file


def find_latest_stockdetalle_file():
    """
    Busca el archivo de stock detalle más reciente en la carpeta downloads
    
    Returns:
        str: Ruta al archivo encontrado o None si no se encuentra
    """
    if not os.path.exists(DOWNLOADS_DIR):
        print(f"Error: La carpeta {DOWNLOADS_DIR} no existe")
        return None
    
    # Busca archivos que contengan "stockdetalle" o "stock_detalle" en el nombre
    stockdetalle_files = []
    for filename in os.listdir(DOWNLOADS_DIR):
        if ("stockdetalle" in filename.lower() or "stock_detalle" in filename.lower()) and filename.endswith('.xlsx'):
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            stockdetalle_files.append((file_path, os.path.getmtime(file_path)))
    
    if not stockdetalle_files:
        print("No se encontraron archivos de stock detalle en la carpeta downloads")
        return None
    
    # Retorna el archivo más reciente
    latest_file = max(stockdetalle_files, key=lambda x: x[1])[0]
    print(f"Archivo de stock detalle encontrado: {latest_file}")
    return latest_file


def find_latest_mermasventas_file():
    """
    Busca el archivo de Mermas y Ventas por Artículo más reciente en la carpeta downloads
    
    Returns:
        str: Ruta al archivo encontrado o None si no se encuentra
    """
    if not os.path.exists(DOWNLOADS_DIR):
        print(f"Error: La carpeta {DOWNLOADS_DIR} no existe")
        return None
    
    # Busca archivos que contengan "mermasventas", "mermas_ventas", "mermas y ventas" en el nombre
    mermasventas_files = []
    for filename in os.listdir(DOWNLOADS_DIR):
        filename_lower = filename.lower()
        if (("mermasventas" in filename_lower or 
             "mermas_ventas" in filename_lower or 
             "mermas y ventas" in filename_lower or
             "mermas" in filename_lower) and 
            filename.endswith('.xlsx')):
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            mermasventas_files.append((file_path, os.path.getmtime(file_path)))
    
    if not mermasventas_files:
        print("No se encontraron archivos de Mermas y Ventas por Artículo en la carpeta downloads")
        return None
    
    # Retorna el archivo más reciente
    latest_file = max(mermasventas_files, key=lambda x: x[1])[0]
    print(f"Archivo de Mermas y Ventas por Artículo encontrado: {latest_file}")
    return latest_file


def test_excel_parsing():
    """
    Función de prueba para convertir el Excel existente a JSON
    """
    print("\n=== CONVERSIÓN EXCEL TO JSON ===")
    
    excel_file = find_latest_catalogados_file()
    
    if excel_file:
        output_json = f"{DOWNLOADS_DIR}/catalogados_data.json"
        json_data = parse_excel_to_json(excel_file, output_json, report_type='catalogados')
        
        if json_data:
            print(f"✓ Conversión exitosa: {len(json_data)} registros")
            return json_data
        else:
            print("✗ Error en la conversión")
            return None
    else:
        print("✗ No se encontró archivo Excel")
        return None


def test_stockdetalle_parsing():
    """
    Función de prueba para convertir el Excel de Stock Detalle a JSON
    """
    print("\n=== CONVERSIÓN STOCK DETALLE EXCEL TO JSON ===")
    
    excel_file = find_latest_stockdetalle_file()
    
    if excel_file:
        output_json = f"{DOWNLOADS_DIR}/stockdetalle_data.json"
        json_data = parse_excel_to_json(excel_file, output_json, report_type='stockdetalle')
        
        if json_data:
            print(f"✓ Conversión exitosa: {len(json_data)} registros")
            return json_data
        else:
            print("✗ Error en la conversión")
            return None
    else:
        print("✗ No se encontró archivo Excel de Stock Detalle")
        return None


def test_mermasventas_parsing():
    """
    Función de prueba para convertir el Excel de Mermas y Ventas por Artículo a JSON
    """
    print("\n=== CONVERSIÓN MERMAS Y VENTAS EXCEL TO JSON ===")
    
    excel_file = find_latest_mermasventas_file()
    
    if excel_file:
        output_json = f"{DOWNLOADS_DIR}/mermasventas_data.json"
        json_data = parse_excel_to_json(excel_file, output_json, report_type='mermasventas')
        
        if json_data:
            print(f"✓ Conversión exitosa: {len(json_data)} registros")
            return json_data
        else:
            print("✗ Error en la conversión")
            return None
    else:
        print("✗ No se encontró archivo Excel de Mermas y Ventas por Artículo")
        return None