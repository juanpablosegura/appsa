import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import base64

# --- Funciones de Parseo (SIN CAMBIOS) ---

def parsear_factura(xml_root):
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
        # Si falta una etiqueta (como en un RIDE), retorna None
        return None

def parsear_retencion(xml_root):
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
        # Si falta una etiqueta, retorna None
        return None

# --- Función de descarga (SIN CAMBIOS) ---

def get_table_download_link(df_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="reporte_sri.xlsx">Descargar Reporte en Excel</a>'
    return href

# --- Interfaz de Streamlit ---

st.set_page_config(layout="wide")
st.title(" visor de Comprobantes del SRI 🧾")
st.markdown("""
Sube los archivos `.xml` que descargaste del portal del SRI para ver tus facturas y retenciones.
""")

uploaded_files = st.file_uploader("📂 Arrastra y suelta tus archivos .xml aquí", 
                                  type="xml", 
                                  accept_multiple_files=True)

if uploaded_files:
    facturas_data = []
    retenciones_data = []

    # --- BUCLE DE PROCESAMIENTO MEJORADO ---
    for xml_file in uploaded_files:
        try:
            xml_content = xml_file.read()
            root = ET.fromstring(xml_content)
            
            # Identificar el tipo de comprobante
            if root.tag == 'factura':
                factura = parsear_factura(root)
                if factura:
                    facturas_data.append(factura)
                else:
                    st.warning(f"El archivo '{xml_file.name}' parece ser una factura, pero no se pudieron leer sus datos internos. ¿Quizás es un RIDE?")
            
            elif root.tag == 'comprobanteRetencion':
                retenciones = parsear_retencion(root)
                if retenciones:
                    retenciones_data.extend(retenciones)
                else:
                    st.warning(f"El archivo '{xml_file.name}' parece ser una retención, pero no se pudieron leer sus datos internos. ¿QuizS es un RIDE?")
            
            else:
                # El archivo es XML, pero no es un tipo conocido
                st.warning(f"El archivo '{xml_file.name}' es un XML válido, pero su tipo ('{root.tag}') no es 'factura' ni 'comprobanteRetencion'. Es probable que sea un RIDE.")

        except ET.ParseError as e:
            # ¡El error más probable! El archivo NO es un XML válido (es HTML)
            st.error(f"Error al procesar '{xml_file.name}': El archivo no es un XML válido. Es muy probable que sea un RIDE (archivo HTML).")
        except Exception as e:
            # Otro error inesperado
            st.error(f"Error inesperado con '{xml_file.name}': {e}")

    # --- Mostrar resultados (SIN CAMBIOS) ---
    
    st.divider() # Separador visual

    if facturas_data:
        st.header("Facturas Procesadas Exitosamente")
        df_facturas = pd.DataFrame(facturas_data)
        total_facturado = df_facturas['Importe Total'].sum()
        st.metric("Total Facturado", f"${total_facturado:,.2f}")
        st.dataframe(df_facturas)
    else:
        st.info("No se encontraron facturas válidas en los archivos subidos.")

    if retenciones_data:
        st.header("Retenciones Procesadas Exitosamente")
        df_retenciones = pd.DataFrame(retenciones_data)
        total_retenido = df_retenciones['Valor Retenido'].sum()
        st.metric("Total Retenido", f"${total_retenido:,.2f}")
        st.dataframe(df_retenciones)
    else:
        st.info("No se encontraron retenciones válidas en los archivos subidos.")

    if facturas_data or retenciones_data:
        st.header("Descargar Datos Consolidados")
        report_dict = {}
        if facturas_data:
            report_dict["Facturas"] = df_facturas
        if retenciones_data:
            report_dict["Retenciones"] = df_retenciones
        st.markdown(get_table_download_link(report_dict), unsafe_allow_html=True)
