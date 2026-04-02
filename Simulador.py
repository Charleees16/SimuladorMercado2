import streamlit as st
import pandas as pd
import qrcode
import random
from streamlit_autorefresh import st_autorefresh
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# streamlit run SimuladorEquipos.py

st.set_page_config(page_title="Simulador Mercado Eléctrico", layout="wide")

# --- MEMORIA COMPARTIDA (BASE DE DATOS EN MEMORIA) ---
@st.cache_resource
def obtener_base_de_datos():
    return {"salas": {}}

db = obtener_base_de_datos()

HORARIOS = [
    {"hora": "08:00 - 09:00", "demanda": 8790, "renovables": 4900},
    {"hora": "09:00 - 10:00", "demanda": 9271, "renovables": 6600},
    {"hora": "10:00 - 11:00", "demanda": 9700, "renovables": 8800},
    {"hora": "11:00 - 12:00", "demanda": 9100, "renovables": 4100},
    {"hora": "12:00 - 13:00", "demanda": 8750, "renovables": 2750},
]

def grafico_merit_order(df_resultado, demanda_residual, precio_marginal):
    # 4. Mapeo exacto de los emojis que pediste
    DICT_NOMBRES_EMOJIS = {
        "Nuclear": "☢️ Nuclear",
        "Carbón": "🪨 Carbón",
        "Ciclo Combinado": "💨 Ciclo",
        "Gas": "🔥 Gas"
    }
    
    # Colores actualizados para los nuevos nombres
    COLORES_TECH = {
        "☢️ Nuclear": "#F5B731",
        "🪨 Carbón":  "#57534E",
        "💨 Ciclo":   "#A8A29E",
        "🔥 Gas":     "#D6D3D1",
    }

    df_sorted = df_resultado.sort_values("Precio (€/MWh)").reset_index(drop=True)
    # Aplicar el cambio de nombre con emojis al dataframe antes de procesarlo
    df_sorted["Tecnología"] = df_sorted["Tecnología"].map(lambda x: DICT_NOMBRES_EMOJIS.get(x, x))
    df_sorted = df_sorted[df_sorted["Potencia Ofertada (MW)"] > 0]

    # --- PARCHE DE SEGURIDAD: Si la gente oferta 0 MW ---
    if df_sorted.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, "Nadie ofertó potencia.\nMercado desierto.", ha='center', va='center', fontsize=15, color="red")
        ax.axis('off')
        return fig

    total_ofertado   = df_sorted["Potencia Ofertada (MW)"].sum()
    
    # --- PARCHE DE SEGURIDAD: Evitar errores de max() con NaN ---
    max_precio_ofertado = df_sorted["Precio (€/MWh)"].max()
    if pd.isna(max_precio_ofertado):
        max_precio_ofertado = 0
        
    max_price_display = max(precio_marginal * 1.45, max_precio_ofertado * 1.2)
    if max_price_display <= 0:
        max_price_display = 100 
    
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    cumulative   = 0
    tech_ranges  = {}

    for _, row in df_sorted.iterrows():
        tech   = row["Tecnología"]
        mw     = row["Potencia Ofertada (MW)"]
        price  = row["Precio (€/MWh)"]

        x_start = (cumulative / demanda_residual) * 100
        x_width = (mw          / demanda_residual) * 100

        # 2. Lógica de colores: si empieza antes del 100%, se colorea (incluye la marginal).
        # Si empieza en el 100% o más tarde, se queda en gris claro (descartadas).
        if x_start < 100:
            color = COLORES_TECH.get(tech, "#F5B731")
        else:
            color = "#F3F4F6" # Gris muy claro para las ofertas no casadas

        rect = plt.Rectangle(
            (x_start, 0), x_width, price,
            facecolor=color, edgecolor="white", linewidth=1.5, zorder=2
        )
        ax.add_patch(rect)

        tech_ranges.setdefault(tech, []).append((x_start, x_start + x_width))
        cumulative += mw

    # ── Área amarilla ──────────────────────────────────────────────────────────
    demand_pct = min((cumulative / demanda_residual) * 100, 100)
    ax.fill_between([0, 100], 0, precio_marginal,
                    color="#FEFCE8", alpha=0.85, zorder=0)

    # ── Líneas punteadas del precio marginal ───────────────────────────────────
    ax.hlines(precio_marginal, 0, 100,
              colors="#1E3A8A", linestyles="--", linewidth=1.6, zorder=4)
    ax.vlines(100, 0, precio_marginal,
              colors="#1E3A8A", linestyles="--", linewidth=1.6, zorder=4)

    # ── Punto azul en la intersección ─────────────────────────────────────────
    ax.plot(100, precio_marginal, "o",
            color="#1E3A8A", markersize=9, zorder=5)

    # 1. ELIMINADA la anotación con flecha y texto largo para una gráfica limpia

    # ── Ejes ──────────────────────────────────────────────────────────────────
    x_max_data = max((total_ofertado / demanda_residual) * 100, 100) * 1.1 # Reducido un poco el espacio derecho al quitar el texto
    ax.set_xlim(-3, x_max_data)
    ax.set_ylim(0, max_price_display)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#E5E7EB")
    ax.spines["bottom"].set_color("#E5E7EB")
    ax.tick_params(colors="#4B5563", length=4)

    # ── Etiquetas de tecnología y Porcentajes en X ────────────────────────────
    xtick_pos, xtick_labels = [], []
    for tech, ranges in tech_ranges.items():
        center = (min(r[0] for r in ranges) + max(r[1] for r in ranges)) / 2
        xtick_pos.append(center)
        xtick_labels.append(tech)

    # 3. Añadimos el 100% explícitamente en el eje X
    xtick_pos.append(100)
    xtick_labels.append("100%\n(Demanda)")

    ax.set_xticks(xtick_pos)
    ax.set_xticklabels(xtick_labels, fontsize=10, color="#4B5563", fontweight="bold")
    
    # 3. Añadimos el precio marginal exacto en el eje Y
    ax.set_yticks([precio_marginal])
    ax.set_yticklabels([f"{precio_marginal:,.2f} €/MWh"], fontsize=11, color="#1E3A8A", fontweight="bold")

    plt.tight_layout()
    return fig

# --- ENRUTADOR MÁGICO ---
params = st.query_params
sala_url = params.get("sala", None)

if sala_url:
    st.session_state.rol = "jugador"
    st.session_state.sala_activa = sala_url
else:
    if "rol" not in st.session_state:
        st.session_state.rol = "host"

@st.dialog("📊 Capacidad y costes de las Centrales", width="large")

def mostrar_ficha_tecnica(sala_id):
    st.markdown("Consulta aquí los parámetros de tu equipo:")
    
    datos_tecnicos = {
        "Parámetro": [
            "Potencia Máx. (MW)",
            "Cambio Máx. por Hora (MW)",
            "Coste Operativo (€/MWh)",
            "Coste por Cambio (€/MW)",
            "Coste Parada/Arranque (€)"
        ]
    }
    
    # Leemos de la "db" compartida usando el sala_id
    for tech, info in db["salas"][sala_id]["TECNOLOGIAS"].items():
        datos_tecnicos[tech] = [
            f"{info['pot_max']:,.0f}",
            f"{info['max_cambio']:,.0f}" if info['max_cambio'] < info['pot_max'] else "Sin límite",
            f"{info['coste_op']:,.2f}",
            f"{info['coste_cambio']:,.0f}",
            f"{info['coste_pa']:,.0f}"
        ]
    
    df_tecnico = pd.DataFrame(datos_tecnicos)
    # Ocultamos el índice y aplicamos los estilos
    styled_df_tec = df_tecnico.style.hide(axis="index").apply(
        lambda x: ['font-weight: bold; border-right: 2px solid #9ca3af;' if x.name == 'Parámetro' else '' for _ in x]
    )
    # Usamos st.table para hacerla 100% estática
    st.table(styled_df_tec)

# ==========================================
# 👑 VISTA DEL CREADOR DE LA SALA (HOST)
# ==========================================
if st.session_state.rol == "host":
    
    # 1. GENERAR SALA
    if "sala_activa" not in st.session_state:
        st.title("⚡¡Bienvenido! Eres el operador del mercado (REE)")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("👥 Generar Sala", type="primary", use_container_width=True):
                nuevo_pin = str(random.randint(1000, 9999))
                db["salas"][nuevo_pin] = {"estado": "esperando", "equipos": []}
                st.session_state.sala_activa = nuevo_pin
                st.rerun()
        st.stop() # Detenemos aquí para que no se vea nada más

    sala_id = st.session_state.sala_activa
    sala = db["salas"][sala_id]
    estado_sala = sala["estado"]
    
    # 2. LOBBY DE ESPERA
    if estado_sala == "esperando":
        st.title("⚡ Sala de Espera")
        URL_BASE = "https://simuladormercado2-jyyg36vuwjm4cvjvepsvs9.streamlit.app" 
        url_invitacion = f"{URL_BASE}/?sala={sala_id}"
        
        col_izq, col_der = st.columns([1, 1])
        with col_izq:
            st.markdown("### 📲 ¡Escanea para participar!")
            st.code(url_invitacion)
            equipos_unidos = sala["equipos"]
            st.markdown(f"### 👥 Empresas registradas: {len(equipos_unidos)}")
            
            if len(equipos_unidos) > 0:
                nombres_html = " ".join([f"<span style='background-color: #1e3a8a; color: white; padding: 10px; border-radius: 10px; margin: 5px; display: inline-block;'>{eq}</span>" for eq in equipos_unidos])
                st.markdown(nombres_html, unsafe_allow_html=True)
            else:
                st.warning("Esperando a que las empresas energéticas se conecten...")
            
            # 👇 CÓDIGO NUEVO SUSTITUYENDO AL BOTÓN
            st_autorefresh(interval=2000, key="refresh_host_lobby")
            
        with col_der:
            qr = qrcode.make(url_invitacion)
            st.image(qr.get_image(), width=350)
        
        st.divider()
        if st.button("🚀 Empezar Partida", type="primary", use_container_width=True):
            if len(equipos_unidos) >= 2:
                sala["estado"] = "jugando"
                factor = 4 / len(equipos_unidos)
                sala["TECNOLOGIAS"] = {
                    "Nuclear": {"pot_max": int(970 * factor), "coste_op": 8.0, "max_cambio": int(100 * factor), "coste_cambio": 70, "coste_pa": 150000},
                    "Carbón": {"pot_max": int(830 * factor), "coste_op": 86.0, "max_cambio": int(200 * factor), "coste_cambio": 50, "coste_pa": 70000},
                    "Ciclo Combinado": {"pot_max": int(800 * factor), "coste_op": 121.0, "max_cambio": int(400 * factor), "coste_cambio": 30, "coste_pa": 10000},
                    "Gas": {"pot_max": int(500 * factor), "coste_op": 168.0, "max_cambio": int(500 * factor), "coste_cambio": 0, "coste_pa": 0}
                }
                sala["dinero_acumulado"] = {eq: 500000 for eq in equipos_unidos}
                sala["energia_acumulada"] = {eq: {tech: 0 for tech in sala["TECNOLOGIAS"].keys()} for eq in equipos_unidos}
                
                # 👇 AQUÍ ESTÁN LAS VARIABLES QUE FALTABAN INICIALIZAR 👇
                sala["ronda_actual"] = 0
                sala["fase"] = "ofertando"
                sala["ofertas"] = {}
                sala["potencia_asignada_anterior"] = {}
                sala["hubo_apagon"] = False
                # 👆 ------------------------------------------------ 👆

                st.rerun()
            else:
                st.error("¡Se necesitan al menos 2 empresas para que haya mercado!")

    # 3. JUEGO ACTIVO (HOST)
    elif estado_sala == "jugando":
        ronda = sala["ronda_actual"]
        
        # PANTALLA DE FIN DE JUEGO
        if ronda >= len(HORARIOS):
            st.success("🎉 ¡La jornada ha terminado! Aquí tenéis los resultados finales.")
            st.balloons()
            st.markdown("<h1 style='text-align: center;'>🏆 CLASIFICACIÓN FINAL 🏆</h1>", unsafe_allow_html=True)
            clasificacion = sorted(sala["dinero_acumulado"].items(), key=lambda x: x[1], reverse=True)
            cols_lb = st.columns(len(sala["equipos"])) 
            medallas = ["🥇 1º PUESTO", "🥈 2º PUESTO", "🥉 3º PUESTO", "🏅 4º PUESTO", "🏅 5º PUESTO"]
            
            for i, (equipo_lb, saldo_lb) in enumerate(clasificacion):
                with cols_lb[i]:
                    with st.container(border=True):
                        st.markdown(f"<h3 style='text-align: center;'>{medallas[i]}</h3>", unsafe_allow_html=True)
                        st.markdown(f"<h4 style='text-align: center;'>{equipo_lb}</h4>", unsafe_allow_html=True)
                        color = "#28a745" if saldo_lb >= 0 else "#dc3545"
                        st.markdown(f"<h2 style='text-align: center; color: {color};'>{saldo_lb:,.0f} €</h2>", unsafe_allow_html=True)
            st.stop()

        datos_hora = HORARIOS[ronda]
        demanda_total = datos_hora["demanda"]
        renovables = datos_hora["renovables"]
        demanda_residual = demanda_total - renovables
        
        # Calculamos los porcentajes para la barrita gráfica
        pct_renovables = (renovables / demanda_total) * 100
        pct_residual = 100 - pct_renovables
        
        st.title(f"⚡ REE - Control Central | {datos_hora['hora']}")
        
        # OJO AQUÍ: La variable sí está alineada con el resto del código Python
        html_visual = f"""
<div style="background-color: #fffbeb; padding: 25px; border-radius: 15px; border: 2px solid #f59e0b; margin-bottom: 20px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
<div style="display: flex; justify-content: space-around; text-align: center; align-items: center; flex-wrap: wrap;">
<div style="margin: 10px;">
<h3 style="color: #b45309; margin: 0; font-size: 1.3rem;">🏭 DEMANDA TOTAL</h3>
<h1 style="font-size: 3rem; color: #d97706; margin: 0;"><strong>{demanda_total} MW</strong></h1>
</div>
<div style="margin: 10px;">
<h1 style="font-size: 3rem; color: #9ca3af; margin: 0;"><strong>-</strong></h1>
</div>
<div style="margin: 10px;">
<h3 style="color: #166534; margin: 0; font-size: 1.3rem;">🌱 RENOVABLES</h3>
<h1 style="font-size: 3rem; color: #22c55e; margin: 0;"><strong>{renovables} MW</strong></h1>
</div>
<div style="margin: 10px;">
<h1 style="font-size: 3rem; color: #9ca3af; margin: 0;"><strong>=</strong></h1>
</div>
<div style="margin: 10px; padding: 10px 20px; background-color: #fef3c7; border-radius: 10px; border: 2px dashed #ea580c;">
<h3 style="color: #ea580c; margin: 0; font-size: 1.3rem;">⚡ A CUBRIR</h3>
<h1 style="font-size: 3.5rem; color: #ea580c; margin: 0;"><strong>{demanda_residual} MW</strong></h1>
</div>
</div>
<div style="margin-top: 25px;">
<p style="text-align: center; margin-bottom: 8px; color: #4b5563; font-weight: bold; font-size: 1.1rem;">Mix Energético</p>
<div style="width: 100%; background-color: #e5e7eb; border-radius: 20px; height: 35px; display: flex; overflow: hidden; border: 1px solid #d1d5db;">
<div style="width: {pct_renovables}%; background-color: #22c55e; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 1rem;">
🌱 {pct_renovables:.1f}% 
</div>
<div style="width: {pct_residual}%; background-color: #f59e0b; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 1rem;">
⚡ {pct_residual:.1f}% 
</div>
</div>
</div>
</div>
"""

        # Y el st.markdown también lleva su sangría para no romper Python
        st.markdown(html_visual, unsafe_allow_html=True)
        
        # FASE: OFERTANDO (HOST ESPERA)
        if sala["fase"] == "ofertando":
            ofertas_recibidas = len(sala["ofertas"])
            total_equipos = len(sala["equipos"])
            
            st.metric("Empresas que han enviado sus ofertas:", f"{ofertas_recibidas} de {total_equipos}")
            st.progress(ofertas_recibidas / total_equipos)
            
            st_autorefresh(interval=2000, key="refresh_host_ofertando")
            
            if st.button("⚖️ Casar Mercado", type="primary", use_container_width=True):
                    if ofertas_recibidas == 0:
                        st.warning("Nadie ha enviado ofertas aún.")
                    else:
                        todas_las_ofertas = []
                        for lista_equipo in sala["ofertas"].values():
                            todas_las_ofertas.extend(lista_equipo)
                            
                        df = pd.DataFrame(todas_las_ofertas)
                        df = df.sort_values(by="Precio (€/MWh)").reset_index(drop=True)
                        df["Potencia Acumulada (MW)"] = df["Potencia Ofertada (MW)"].cumsum()
                        df["Potencia Previa (MW)"] = df["Potencia Acumulada (MW)"] - df["Potencia Ofertada (MW)"]
                        
                        def calcular_asignacion(row):
                            if row["Potencia Previa (MW)"] >= demanda_residual: return 0
                            elif row["Potencia Acumulada (MW)"] <= demanda_residual: return row["Potencia Ofertada (MW)"]
                            else: return demanda_residual - row["Potencia Previa (MW)"]
                                
                        df["Potencia Asignada (MW)"] = df.apply(calcular_asignacion, axis=1)
                        ofertas_aceptadas = df[df["Potencia Asignada (MW)"] > 0]
                        precio_marginal = df.iloc[0]["Precio (€/MWh)"] if ofertas_aceptadas.empty else ofertas_aceptadas.iloc[-1]["Precio (€/MWh)"]
                        
                        df["Ingresos (€)"] = df["Potencia Asignada (MW)"] * precio_marginal
                        df["Costes Op (€)"] = df["Potencia Asignada (MW)"] * df["Coste Op (€/MWh)"]
                        
                        if sala["ronda_actual"] == 0:
                            df["Penalización Cambio (€)"] = 0
                            df["Penalización Parada/Arranque (€)"] = 0
                        else:
                            df["Cambio Carga (MW)"] = abs(df["Potencia Asignada (MW)"] - df["Potencia Anterior (MW)"])
                            df["Penalización Cambio (€)"] = df["Cambio Carga (MW)"] * df["Coste Cambio (€/MW)"]
                            def calcular_pa(row):
                                if row["Potencia Anterior (MW)"] == 0 and row["Potencia Asignada (MW)"] > 0: return row["Coste P/A Fijo (€)"]
                                elif row["Potencia Anterior (MW)"] > 0 and row["Potencia Asignada (MW)"] == 0: return row["Coste P/A Fijo (€)"]
                                else: return 0
                            df["Penalización Parada/Arranque (€)"] = df.apply(calcular_pa, axis=1)
                        
                        df["Beneficio Neto (€)"] = df["Ingresos (€)"] - df["Costes Op (€)"] - df["Penalización Cambio (€)"] - df["Penalización Parada/Arranque (€)"]
                        
                        total_asignado = df["Potencia Asignada (MW)"].sum()
                        if total_asignado < demanda_residual:
                            sala["hubo_apagon"] = True
                        else:
                            sala["hubo_apagon"] = False
                            # Actualizar balances
                            for _, row in df.iterrows():
                                eq = row['Equipo']
                                tech = row['Tecnología']
                                clave = f"{eq}_{tech}"
                                sala["potencia_asignada_anterior"][clave] = row["Potencia Asignada (MW)"]
                                sala["dinero_acumulado"][eq] += row["Beneficio Neto (€)"]
                                sala["energia_acumulada"][eq][tech] += row["Potencia Asignada (MW)"]
                        
                        # Guardamos resultados en la base de datos
                        sala["resultados_df"] = df.to_dict('records') # Guardamos como diccionario para evitar problemas de hilos
                        sala["precio_marginal"] = float(precio_marginal)
                        sala["fase"] = "resultados"
                        st.rerun()

        # FASE: RESULTADOS GLOBALES (HOST)
        elif sala["fase"] == "resultados":
            

            datos_hora_res  = HORARIOS[ronda]
            demanda_res_now = datos_hora_res["demanda"] - datos_hora_res["renovables"]
            df_res = pd.DataFrame(sala["resultados_df"])
            fig_merit = grafico_merit_order(df_res, demanda_res_now, sala["precio_marginal"])
            # --------------------------------------------------------

            if sala["hubo_apagon"]:
                st.markdown("<h1 style='text-align: center; color: #ff0000; font-size: 4em;'>🚨 ¡ALERTA APAGÓN! 🚨</h1>", unsafe_allow_html=True)
                st.error("El sistema eléctrico está al borde del colapso. El mercado ha sido anulado.")
                
                # LA MOSTRAMOS TAMBIÉN DURANTE EL APAGÓN
                st.pyplot(fig_merit)
                plt.close(fig_merit)
                
                if st.button("🔄 Obligar a rehacer Ofertas", type="primary"):
                    sala["fase"] = "ofertando"
                    sala["ofertas"] = {}
                    sala["hubo_apagon"] = False
                    st.rerun()
            else:
                st.success(f"### 💰 Precio Final del Mercado: {sala['precio_marginal']:,.2f} €/MWh")

                # LA MOSTRAMOS CUANDO TODO VA BIEN
                st.pyplot(fig_merit)
                plt.close(fig_merit)
                
                # Resumen de beneficios para el profe
                df_res = pd.DataFrame(sala["resultados_df"])
                resumen = df_res.groupby("Equipo")["Beneficio Neto (€)"].sum().reset_index()
                st.table(resumen.style.hide(axis="index"))
                
                if st.button("⏭️ Avanzar a la Siguiente Hora", type="primary", use_container_width=True):
                    sala["ronda_actual"] += 1
                    sala["fase"] = "ofertando"
                    sala["ofertas"] = {}
                    st.rerun()

# ==========================================
# 📱 VISTA DEL JUGADOR (EMPRESA)
# ==========================================
if st.session_state.rol == "jugador":
    sala_id = st.session_state.sala_activa
    
    if sala_id not in db["salas"]:
        st.error("❌ Esta sala no existe o la partida ya terminó.")
        st.stop()
        
    sala = db["salas"][sala_id]
    estado_sala = sala["estado"]
    
    # REGISTRO
    if estado_sala == "esperando":
        st.title("🏢 Registro de Empresa")
        if "mi_equipo" not in st.session_state:
            nombre_equipo = st.text_input("Nombre de tu empresa:")
            if st.button("Aceptar", type="primary"):
                if nombre_equipo and nombre_equipo not in sala["equipos"]:
                    sala["equipos"].append(nombre_equipo)
                    st.session_state.mi_equipo = nombre_equipo
                    st.rerun()
                else:
                    st.error("Nombre inválido o en uso.")
        else:
            st.success(f"✅ ¡Tu empresa **{st.session_state.mi_equipo}** se ha registrado con éxito! La jornada de mercado empezará muy pronto...")
            
            st_autorefresh(interval=2000, key="refresh_jugador_lobby")
        st.stop() 
        
    elif estado_sala == "jugando" and "mi_equipo" not in st.session_state:
        st.error("Llegaste tarde, la partida ya ha empezado.")
        st.stop()

    # JUEGO ACTIVO (JUGADOR)
    mi_equipo = st.session_state.mi_equipo
    ronda = sala["ronda_actual"]
    
    # FIN DEL JUEGO
    if ronda >= len(HORARIOS):
        st.success("🎉 ¡El mercado ha cerrado por hoy!")
        st.info("Mira la pantalla del profesor para ver la clasificación final.")
        st.stop()

    datos_hora = HORARIOS[ronda]
    demanda_residual = datos_hora["demanda"] - datos_hora["renovables"]
    
    st.title(f"🏢 {mi_equipo}")
    
# Ponemos la información principal directamente en la pantalla, ideal para el móvil
    st.info(f"🕒 **HORA:** {datos_hora['hora']}\n\n🏭 **DEMANDA A CUBRIR:** {demanda_residual} MW")
    
    # Botón gigante y accesible en el móvil para abrir el Modal
    if st.button("🔍 Ver Capacidad y Costes de mis Centrales", use_container_width=True):
        mostrar_ficha_tecnica(sala_id)
        
    st.divider()
    
    # FASE: ENVIAR OFERTAS
    if sala["fase"] == "ofertando":
        if mi_equipo in sala["ofertas"]:
            st.success("📤 Oferta enviada a REE.")
            st.info("Esperando a que el resto de empresas envíen y REE case el mercado...")
            # 👇 NUEVO: Refresco automático
            st_autorefresh(interval=2000, key="refresh_jugador_esperando")
        else:
            st.subheader("📝 Prepara tu oferta")
            mis_ofertas = []
            
            with st.form(key=f"form_oferta_{ronda}"):
                for tech, info in sala["TECNOLOGIAS"].items():
                    clave_historial = f"{mi_equipo}_{tech}"
                    pot_anterior = sala["potencia_asignada_anterior"].get(clave_historial, 0)
                    
                    st.markdown(f"**🔌 {tech}** (Anterior: {pot_anterior} MW)")
                    col1, col2 = st.columns(2)
                    with col1:
                        if ronda == 0:
                            min_sl, max_sl = 0, info['pot_max']
                        else:
                            min_sl = int(max(0, pot_anterior - info['max_cambio']))
                            max_sl = int(min(info['pot_max'], pot_anterior + info['max_cambio']))
                            
                        pot = st.slider(f"MW - {tech}", min_sl, max_sl, int(pot_anterior) if pot_anterior >= min_sl else min_sl, step=10)
                    with col2:
                        pre = st.number_input(f"€/MWh - {tech}", value=float(info['coste_op']), step=1.0)
                        
                    mis_ofertas.append({
                        "Equipo": mi_equipo, "Tecnología": tech, "Potencia Ofertada (MW)": pot, 
                        "Precio (€/MWh)": pre, "Coste Op (€/MWh)": info['coste_op'], 
                        "Coste Cambio (€/MW)": info['coste_cambio'], "Coste P/A Fijo (€)": info['coste_pa'],
                        "Potencia Anterior (MW)": pot_anterior
                    })
                    st.divider()
                
                enviado = st.form_submit_button("⚖️ Enviar Oferta ", type="primary", use_container_width=True)
                if enviado:
                    sala["ofertas"][mi_equipo] = mis_ofertas
                    st.rerun()

    # FASE: VER RESULTADOS PRIVADOS
    elif sala["fase"] == "resultados":
        if sala["hubo_apagon"]:
            st.error("🚨 ¡APAGÓN! No se cubrió la demanda. Prepárate para rehacer la oferta.")
            st_autorefresh(interval=2000, key="refresh_jugador_apagon")
        else:
            st.success("✅ Mercado Casado. Aquí están tus resultados.")
            
            df_res = pd.DataFrame(sala["resultados_df"])
            datos_mios = df_res[df_res["Equipo"] == mi_equipo]
            
            saldo_actual = sala["dinero_acumulado"][mi_equipo]
            
            # Tabla bonita adaptada a datos_mios
            tecnologias_orden = ["Nuclear", "Carbón", "Ciclo Combinado", "Gas"]
            emojis_tech = {"Nuclear": "☢️ Nuclear", "Carbón": "🪨 Carbón", "Ciclo Combinado": "💨 Ciclo", "Gas": "🔥 Gas"}
            
            data_dict = {
                "Concepto": [
                    "Oferta - Potencia (MW)", "Oferta - Precio (€/MWh)",
                    "Vendido - Potencia (MW)", f"Precio Cierre (€/MWh)",
                    "Cuentas - Ingresos (€)", "Cuentas - Costes Op. (€)",
                    "Cuentas - Penalizaciones (€)", "Cuentas - Beneficio Neto (€)"
                ]
            }
            
            for tech in tecnologias_orden:
                tech_disp = emojis_tech[tech]
                row_data = datos_mios[datos_mios["Tecnología"] == tech]
                if not row_data.empty:
                    r = row_data.iloc[0]
                    penalizaciones = r["Penalización Cambio (€)"] + r["Penalización Parada/Arranque (€)"]
                    data_dict[tech_disp] = [
                        f"{r['Potencia Ofertada (MW)']:,.0f}", f"{r['Precio (€/MWh)']:,.2f}",
                        f"{r['Potencia Asignada (MW)']:,.0f}", f"{sala['precio_marginal']:,.2f}" if r["Potencia Asignada (MW)"] > 0 else "0.00",
                        f"{r['Ingresos (€)']:,.0f}", f"{r['Costes Op (€)']:,.0f}",
                        f"{penalizaciones:,.0f}", f"{r['Beneficio Neto (€)']:,.0f}"
                    ]
                else:
                    data_dict[tech_disp] = ["0", "0.00", "0", "0.00", "0", "0", "0", "0"]
                    
            df_display = pd.DataFrame(data_dict)
            
            def aplicar_colores(row):
                concepto = row['Concepto']
                if 'Oferta' in concepto: est = 'background-color: #dbeafe; color: #1e3a8a;' 
                elif 'Vendido' in concepto or 'Ingresos' in concepto: est = 'background-color: #dcfce7; color: #166534;' 
                elif 'Costes' in concepto or 'Penalizaciones' in concepto: est = 'background-color: #fee2e2; color: #991b1b;' 
                elif 'Beneficio Neto' in concepto: est = 'background-color: #16a34a; color: white; font-weight: bold;' 
                else: est = ''
                estilos = [est] * len(row)
                estilos[0] = (est + ' font-weight: bold; border-right: 2px solid gray;') if est else 'font-weight: bold; border-right: 2px solid gray;'
                return estilos

            # Ocultamos el índice al aplicar el estilo
            styled_df = df_display.style.hide(axis="index").apply(aplicar_colores, axis=1)
            # Imprimimos tabla inamovible
            st.table(styled_df)
            
            st.markdown(f"<h3 style='text-align: right; color: #1e3a8a;'>💵 SALDO TOTAL: {saldo_actual:,.0f} €</h3>", unsafe_allow_html=True)
            st.info("Esperando a que el Operador del Mercado (Host) inicie la siguiente hora...")
            
            # 👇 REFRESCO AUTOMÁTICO EN VEZ DEL BOTÓN
            st_autorefresh(interval=2000, key="refresh_jugador_resultados")
