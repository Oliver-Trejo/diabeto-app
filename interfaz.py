import streamlit as st
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import pandas as pd
import joblib

# --- CONFIGURACIONES GLOBALES ---
st.set_page_config(page_title="DIABETO", page_icon="🏥", layout="wide")
RUTA_MODELO = "modelo_rf_entrenado.pkl"
RUTA_PREGUNTAS = "preguntas_con_codigos.json"
RUTA_CREDENCIALES = "credentials.json"
COLUMNAS_MODELO = [
    "SEXO", "PESO1_1", "TALLA4_1", "P27_1_1", "P27_1_2", "P1_1", "P1_6", "P4_1", "P1_7",
    "P5_1", "P5_2_1", "P6_1_1", "P6_6", "P6_4", "P13_1", "P13_2", "P13_10", "P13_11", "P13_12_1",
    "P7_1_1", "P7_2_1", "P7_3_1", "P7_5_1", "P7_1_2", "P7_2_2", "P7_3_2", "P7_5_2",
    "P7_1_3", "P7_2_3", "P7_3_3", "P7_5_3", "COMIDA_RAP", "DULCES", "CEREALES_DUL"
]

# --- FUNCIONES AUXILIARES ---
def set_background(image_path):
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    st.markdown(f"""
        <style>.stApp {{background-image: url("data:image/png;base64,{encoded}");}}</style>
    """, unsafe_allow_html=True)

def cargar_css(path):
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def conectar_google_sheet(nombre=None, key=None):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Forzamos lectura como cadena y reemplazamos saltos de línea
        raw = st.secrets["gcp_service_account"]
        if isinstance(raw, dict):
            raw = json.dumps(raw)  # En caso de que ya venga como dict, lo retransformamos
        creds_dict = json.loads(raw.replace("\\n", "\n"))
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(key).sheet1 if key else client.open(nombre).sheet1
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets: {e}")
        return None

def render_pregunta(pregunta, key):
    tipo, label = pregunta["tipo"], pregunta["label"]
    if tipo == "text":
        return st.text_input(label, key=key)
    elif tipo == "number":
        return st.number_input(label, key=key)
    elif tipo == "textarea":
        return st.text_area(label, key=key)
    elif tipo == "select":
        opciones = ["Selecciona"] + pregunta["opciones"]
        seleccion = st.selectbox(label, opciones, key=key)
        if "valores" in pregunta and seleccion != "Selecciona":
            return pregunta["valores"][pregunta["opciones"].index(seleccion)]
        return "" if seleccion == "Selecciona" else seleccion

# --- FUNCIONES PRINCIPALES ---
def login_page():
    set_background("Inteligencia Artificial de Apoyo a la Detección de Diabetes Tipo 2.png")
    cargar_css("style.css")
    st.markdown("""<div class='form-container'><div style='text-align:center; margin-bottom:30px;'>
    <h1 style='color:black;'>Inteligencia Artificial<br>Apoyo a la Detección de Diabetes Tipo 2</h1></div>""", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("Correo", placeholder="000000@example.com", label_visibility="collapsed")
        password = st.text_input("Contraseña", type="password", placeholder="Contraseña", label_visibility="collapsed")
        if st.form_submit_button("Ingresar"):
            if email == "0000@example.com" and password == "123":
                st.session_state["logged_in"] = True
                st.session_state["usuario"] = email
                st.success("Inicio de sesión exitoso")
                st.rerun()
            else:
                st.error("Correo o contraseña incorrectos")
    st.markdown("</div>", unsafe_allow_html=True)

def mostrar_perfil():
    st.title("🧑‍⚕️ Mi Cuenta")
    st.markdown("""<style>.perfil-container{text-align:center; margin-top:35px;}</style>""", unsafe_allow_html=True)
    st.markdown("<div class='perfil-container'>", unsafe_allow_html=True)
    st.markdown("<h2>Dr. Nombre Apellido Apellido</h2>", unsafe_allow_html=True)
    st.image("imagen_23.webp", width=300)
    st.markdown("<h3>Médico Partero Familiar</h3></div>", unsafe_allow_html=True)

def mostrar_pacientes():
    st.title("📋 Lista de Pacientes Registrados")
    sheet = conectar_google_sheet(key="1C5H_AJQtMCvNdHfs55Hv8vl_LcwAI0_syK85JV1KUv0")
    if sheet is None:
        return
    df = pd.DataFrame(sheet.get_all_records())
    if df.empty:
        st.info("Aún no hay pacientes registrados.")
        return
    if "Nombre" not in df.columns:
        st.error("No se encontró la columna 'Nombre'")
        return
    nombres = df["Nombre"].dropna().unique().tolist()
    seleccionado = st.selectbox("Selecciona un paciente para ver su registro:", ["Selecciona"] + nombres)
    if seleccionado != "Selecciona":
        registro = df[df["Nombre"] == seleccionado].iloc[-1]
        col1, col2 = st.columns([3, 2])
        with col1:
            st.subheader(f"🧾 Registro de {seleccionado}")
        with col2:
            if "Probabilidad Estimada" in registro and "Predicción Óptima" in registro:
                prob = float(registro["Probabilidad Estimada"])
                pred = int(registro["Predicción Óptima"])
                color = "⚠️" if pred == 1 else "✅"
                mensaje = "Riesgo de Diabetes" if pred == 1 else "Sin Riesgo"
                st.markdown(f"""<div style='background-color:#f0f2f6;padding:10px;border-radius:8px;'>
                <b>{color} {mensaje}</b><br>Probabilidad: <b>{prob:.2%}</b></div>""", unsafe_allow_html=True)
        with open(RUTA_PREGUNTAS, encoding="utf-8") as f:
            preguntas_json = json.load(f)
        codigo_a_label = {}
        codigo_a_opciones = {}
        for bloque in ["Generales", "Salud"]:
            for p in preguntas_json[bloque]:
                if "codigo" in p:
                    codigo_a_label[p["codigo"]] = p["label"]
                    if "valores" in p and "opciones" in p:
                        codigo_a_opciones[p["codigo"]] = dict(zip(p["valores"], p["opciones"]))
        for familiar, grupo in preguntas_json["Antecedentes familiares"].items():
            for p in grupo:
                if "codigo" in p:
                    codigo_a_label[p["codigo"]] = p["label"]
                    if "valores" in p and "opciones" in p:
                        codigo_a_opciones[p["codigo"]] = dict(zip(p["valores"], p["opciones"]))
        for campo, valor in registro.items():
            label = codigo_a_label.get(campo, campo)
            if campo in codigo_a_opciones:
                try:
                    valor = codigo_a_opciones[campo].get(int(valor), valor)
                except:
                    pass
            st.markdown(f"**{label}:** {valor}")
        if st.button("🗑️ Eliminar este registro"):
            index_a_eliminar = df[df["Nombre"] == seleccionado].index[-1]
            fila_real = int(index_a_eliminar) + 2
            sheet.delete_rows(fila_real)
            st.success(f"✅ Último registro de {seleccionado} eliminado.")
            st.rerun()

def predecir_nuevos_registros(df_input, threshold=0.18):
    modelo = joblib.load(RUTA_MODELO)
    X = df_input[COLUMNAS_MODELO].replace("", -1).astype(float)
    df_input['Probabilidad Estimada'] = modelo.predict_proba(X)[:, 1]
    df_input['Predicción Óptima'] = (df_input['Probabilidad Estimada'] >= threshold).astype(int)
    return df_input

def guardar_en_google_sheets(fila, proba=None, pred=None):
    sheet = conectar_google_sheet(nombre="Registro_Pacientes")
    if proba is not None and pred is not None:
        fila.extend([float(proba), int(pred)])
    sheet.append_row(fila)

def mostrar_resultado_prediccion(proba, pred):
    color = "#FFA500" if pred == 1 else "#4CAF50"
    emoji = "⚠️" if pred == 1 else "✅"
    titulo = "Riesgo de Diabetes" if pred == 1 else "Sin riesgo estimado"
    st.markdown(f"""
        <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; border-left: 5px solid {color};'>
            <h3 style='color:{color};'>{emoji} {titulo}</h3>
            <p style='font-weight:bold;'>Probabilidad estimada: {proba:.2%}</p>
        </div>
    """, unsafe_allow_html=True)

def ejecutar_prediccion():
    sheet = conectar_google_sheet(key="1C5H_AJQtMCvNdHfs55Hv8vl_LcwAI0_syK85JV1KUv0")
    df = pd.DataFrame(sheet.get_all_records())
    if df.empty:
        st.warning("No hay datos suficientes para predecir.")
        return
    faltantes = [col for col in COLUMNAS_MODELO if col not in df.columns]
    if faltantes:
        st.error(f"Faltan columnas: {faltantes}")
        return
    X = df.iloc[[-1]][COLUMNAS_MODELO].replace("", -1)
    modelo = joblib.load(RUTA_MODELO)
    proba = modelo.predict_proba(X)[0, 1]
    pred = int(proba >= 0.21)
    mostrar_resultado_prediccion(proba, pred)

def nuevo_registro():
    st.title("📝 Registro de Pacientes")
    with open(RUTA_PREGUNTAS, encoding="utf-8") as f:
        secciones = json.load(f)
    respuestas = {}
    if st.session_state.get("mostrar_prediccion"):
        ejecutar_prediccion()
        st.session_state["mostrar_prediccion"] = False

    with st.form("formulario_registro"):
        for titulo, preguntas in secciones.items():
            st.subheader(titulo)
            if titulo == "Antecedentes familiares":
                for familiar, grupo in preguntas.items():
                    st.markdown(f"### {familiar}")
                    for i, p in enumerate(grupo):
                        codigo = p.get("codigo", f"{p['label']}-{i}")
                        respuestas[codigo] = render_pregunta(p, key=codigo)
            else:
                for i, p in enumerate(preguntas):
                    codigo = p.get("codigo", f"{p['label']}-{i}")
                    respuestas[codigo] = render_pregunta(p, key=codigo)
        if st.form_submit_button("Guardar"):
            df_modelo = pd.DataFrame([respuestas])
            resultado = predecir_nuevos_registros(df_modelo)
            proba = resultado["Probabilidad Estimada"].iloc[0]
            pred = resultado["Predicción Óptima"].iloc[0]
            guardar_en_google_sheets(list(respuestas.values()), proba, pred)
            st.success("✅ Registro guardado correctamente.")
            st.session_state["mostrar_prediccion"] = True
            st.rerun()

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if st.session_state["logged_in"]:
        st.sidebar.markdown("## Navegación")
        opcion = st.sidebar.radio("", ["Mi Cuenta", "Nuevo Registro", "Pacientes"])
        st.sidebar.button("🔴 Cerrar sesión", on_click=lambda: st.session_state.update({"logged_in": False, "usuario": None}))
        if opcion == "Mi Cuenta":
            mostrar_perfil()
        elif opcion == "Nuevo Registro":
            nuevo_registro()
        elif opcion == "Pacientes":
            mostrar_pacientes()
    else:
        login_page()

main()
