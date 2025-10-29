import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import base64
# Ya no necesitamos 'zipfile'

# --- Funciones de Parseo (SIN CAMBIOS) ---

def parsear_factura(xml_root):
    """Extrae datos de un XML de factura."""
    try:
        info_tributaria = xml_root.find('infoTributaria')
        info_factura = xml_root.find('infoFactura')
        
        ruc_emisor = info_tributaria.find('ruc').text
        razon_social_emisor = info_tributaria.find('razonSocial').text
        fecha_emision = info_factura.find('fechaEmision').text
        total_sin_impuestos = float(info_factura.find('totalSinImpuestos').text)
        importe_total = float(info_factura.find('importeTotal').text)
        
        return {
            "Tipo": "Factura",
            "Fecha Emisión": fecha_emision,
            "RUC Emisor": ruc_emisor,
            "Razón Social Emisor": razon_social_emisor,
            "Total Sin Impuestos": total_sin_impuestos,
            "Importe Total": importe_total,
        }
    except AttributeError:
        return None

def parsear_retencion(xml_root):
    """Extrae datos de un XML de retención."""
    try:
        info_tributaria = xml_root.find('infoTributaria')
        info_comp = xml_root.find('infoCompRetencion')
        impuestos = xml_root.find('impuestos')
        
        ruc_emisor = info_tributaria.find('ruc').text
        razon_social_emisor = info_tributaria.find('razonSocial').text
        fecha_emision = info_comp.find('fechaEmision').text
        
        datos_retencion = []
        for impuesto in impuestos.findall('impuesto'):
            base_imponible = float(impuesto.find('baseImponible').text)
            porcentaje_retener = float(impuesto.find('porcentajeRetener').text)
            valor_retenido = float(impuesto.find('valorRetenido').text)
            cod_doc_sustento = impuesto.find('codDocSustento').text
            num_doc_sustento = impuesto.find('numDocSustento').text

            datos_retencion.append({
                "Tipo": "Retención",
                "Fecha Emisión": fecha_emision,
                "RUC Agente Retención": ruc_emisor,
                "Razón Social Agente": razon_social_emisor,
                "Factura Afectada": num_doc_sustento,
                "Base Imponible": base_imponible,
                "Porcentaje": porcentaje_retener,
                "Valor Retenido": valor_retenido,
            })
        return datos_retencion
    except AttributeError:
        return None

# --- Función para generar el link de descarga (SIN CAMBIOS) ---

def get_table_download_link(df_dict):
    """Genera un link para descargar un diccionario de DataFrames como un archivo Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="reporte_sri.xlsx">Descargar Reporte en Excel</a>'
    return href

# --- Interfaz de Streamlit (CON CAMBIOS) ---

st.set_page_config(layout="wide")
st.title(" visor de Comprobantes del SRI 🧾")
st.markdown("""
Sube los archivos `.xml` que descargaste del portal del SRI para ver tus facturas y retenciones.
""")

# --- CAMBIO AQUÍ ---
# Ahora acepta múltiples archivos .xml en lugar de un .zip
uploaded_files = st.file_uploader("📂 Arrastra y suelta tus archivos .xml aquí", 
                                  type="xml", 
                                  accept_multiple_files=True)

if uploaded_files: # Si la lista no está vacía
    facturas_data = []
    retenciones_data = []

    # --- CAMBIO AQUÍ ---
    # Iteramos sobre la lista de archivos subidos
    for xml_file in uploaded_files:
        try:
            # Leemos el contenido de cada archivo
            xml_content = xml_file.read()
            
            # Parsear el contenido XML
            root = ET.fromstring(xml_content)
            
            # Identificar el tipo de comprobante
            if root.tag == 'factura':
                factura = parsear_factura(root)
                if factura:
                    facturas_data.append(factura)
            elif root.tag == 'comprobanteRetencion':
                retenciones = parsear_retencion(root)
                if retenciones:
                    retenciones_data.extend(retenciones)
        
        except Exception as e:
            # Avisa si un archivo falla, pero continúa con los demás
            st.warning(f"No se pudo procesar el archivo '{xml_file.name}': {e}")

    # --- El resto del código para mostrar datos es IDÉNTICO ---
    
    # --- Mostrar datos de Facturas ---
    if facturas_data:
        st.header("Facturas Recibidas")
        df_facturas = pd.DataFrame(facturas_data)
        
        total_facturado = df_facturas['Importe Total'].sum()
        st.metric("Total Facturado", f"${total_facturado:,.2f}")
        
        st.dataframe(df_facturas)
    else:
        st.info("No se encontraron facturas en los archivos subidos.")

    # --- Mostrar datos de Retenciones ---
    if retenciones_data:
        st.header("Retenciones Recibidas")
        df_retenciones = pd.DataFrame(retenciones_data)
        
        total_retenido = df_retenciones['Valor Retenido'].sum()
        st.metric("Total Retenido", f"${total_retenido:,.2f}")
        
        st.dataframe(df_retenciones)
    else:
        st.info("No se encontraron retenciones en los archivos subidos.")

    # --- Botón de descarga ---
    if facturas_data or retenciones_data:
        st.header("Descargar Datos Consolidados")
        report_dict = {}
        if facturas_data:
            report_dict["Facturas"] = df_facturas
        if retenciones_data:
            report_dict["Retenciones"] = df_retenciones
            
        st.markdown(get_table_download_link(report_dict), unsafe_allow_html=True)
