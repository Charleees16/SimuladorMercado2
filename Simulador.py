import streamlit as st
import pandas as pd

# streamlit run Simulador.py

st.set_page_config(page_title="Simulador Mercado Eléctrico", layout="wide")
st.title("⚡ Simulador de Mercado Eléctrico ")

# --- DATOS DEL JUEGO ---
TECNOLOGIAS = {
    "Nuclear": {"pot_max": 970, "coste_op": 8.0, "max_cambio": 100, "coste_cambio": 70, "coste_pa": 150000},
    "Carbón (Coal PP)": {"pot_max": 830, "coste_op": 86.0, "max_cambio": 200, "coste_cambio": 50, "coste_pa": 70000},
    "Ciclo Combinado (GTCC)": {"pot_max": 800, "coste_op": 121.0, "max_cambio": 400, "coste_cambio": 30, "coste_pa": 10000},
    "Gas Engine": {"pot_max": 500, "coste_op": 168.0, "max_cambio": 500, "coste_cambio": 0, "coste_pa": 0}
}

HORARIOS = [
    {"hora": "08:00 - 09:00", "demanda": 8790, "renovables": 4900},
    {"hora": "09:00 - 10:00", "demanda": 9271, "renovables": 6600},
    {"hora": "10:00 - 11:00", "demanda": 9700, "renovables": 8800},
    {"hora": "11:00 - 12:00", "demanda": 9100, "renovables": 4100},
    {"hora": "12:00 - 13:00", "demanda": 8750, "renovables": 2750},
]

# --- INICIALIZAR MEMORIA DEL JUEGO ---
if 'ronda_actual' not in st.session_state:
    st.session_state.ronda_actual = 0
    st.session_state.mercado_casado = False
    st.session_state.hubo_apagon = False
    st.session_state.penalizacion_apagon = {}
    st.session_state.potencia_asignada_anterior = {} 
    st.session_state.dinero_acumulado = {"Equipo 1": 500000, "Equipo 2": 500000, "Equipo 3": 500000, "Equipo 4": 500000}
    # NUEVO: Memoria para guardar toda la energía vendida durante la partida
    st.session_state.energia_acumulada = {
        f"Equipo {i}": {tech: 0 for tech in TECNOLOGIAS.keys()} for i in range(1, 5)
    }

ronda = st.session_state.ronda_actual

# --- FINAL DEL JUEGO ---
if ronda >= len(HORARIOS):
    st.success("🎉 ¡La jornada ha terminado! Aquí tenéis los resultados finales.")
    st.balloons()
    
    st.divider()
    st.markdown("<h1 style='text-align: center;'>🏆 CLASIFICACIÓN FINAL 🏆</h1>", unsafe_allow_html=True)
    
    clasificacion = sorted(st.session_state.dinero_acumulado.items(), key=lambda x: x[1], reverse=True)
    cols_lb = st.columns(4)
    medallas = ["🥇 GANADOR", "🥈 SEGUNDO", "🥉 TERCERO", "🏅 CUARTO"]
    
    for i, (equipo_lb, saldo_lb) in enumerate(clasificacion):
        with cols_lb[i]:
            with st.container(border=True):
                st.markdown(f"<h3 style='text-align: center;'>{medallas[i]}</h3>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='text-align: center;'>{equipo_lb}</h4>", unsafe_allow_html=True)
                
                # Dinero
                color = "#28a745" if saldo_lb >= 0 else "#dc3545"
                st.markdown(f"<h2 style='text-align: center; color: {color};'>{saldo_lb:,.0f} €</h2>", unsafe_allow_html=True)
                
                # --- NUEVO: ESTADÍSTICAS DE ENERGÍA ---
                st.divider()
                datos_energia = st.session_state.energia_acumulada[equipo_lb]
                energia_total = sum(datos_energia.values())
                
                st.markdown(f"<p style='text-align: center; font-size: 1.1em;'><b>⚡ Energía Suministrada:</b><br>{energia_total:,.0f} MWh</p>", unsafe_allow_html=True)
                
                # Ordenar tecnologías por aportación (de mayor a menor)
                tech_ordenadas = sorted(datos_energia.items(), key=lambda x: x[1], reverse=True)
                
                html_techs = "<div style='font-size: 0.9em; padding-left: 10px;'>"
                posicion = 1
                for tech, mwh in tech_ordenadas:
                    if mwh > 0:
                        porcentaje = (mwh / energia_total * 100) if energia_total > 0 else 0
                        html_techs += f"<b>{posicion}º {tech}:</b> {mwh:,.0f} MWh <i>({porcentaje:.1f}%)</i><br>"
                        posicion += 1
                
                if energia_total == 0:
                    html_techs += "<i>No generó energía en toda la partida</i>"
                html_techs += "</div><br>"
                
                st.markdown(html_techs, unsafe_allow_html=True)
    
    st.stop()

# --- CÓDIGO NORMAL DE LA RONDA ---
datos_hora = HORARIOS[ronda]
hora_str = datos_hora["hora"]
demanda_residual = datos_hora["demanda"] - datos_hora["renovables"]

# --- PANEL SUPERIOR ---
st.sidebar.header(f"🕒 HORA ACTUAL: {hora_str}")
st.sidebar.progress((ronda + 1) / len(HORARIOS), text=f"Ronda {ronda + 1} de {len(HORARIOS)}")
st.sidebar.info(f"**Demanda Total:** {datos_hora['demanda']} MW\n\n**Renovables:** -{datos_hora['renovables']} MW\n\n---\n**🏭 DEMANDA A CUBRIR:** {demanda_residual} MW")

# --- INTERFAZ DE OFERTAS ---
st.subheader(f"📝 Ofertas para el tramo {hora_str}")

tabs = st.tabs(["Equipo 1", "Equipo 2", "Equipo 3", "Equipo 4"])
ofertas = []

for i, tab in enumerate(tabs):
    equipo = f"Equipo {i+1}"
    with tab:
        for tech, info in TECNOLOGIAS.items():
            clave_historial = f"{equipo}_{tech}"
            pot_anterior = st.session_state.potencia_asignada_anterior.get(clave_historial, 0)
            
            activa = st.toggle(f"🔌 Activar {tech}", value=(pot_anterior > 0 or st.session_state.ronda_actual == 0), key=f"tgl_{equipo}_{tech}_{ronda}", disabled=st.session_state.mercado_casado)
            
            col1, col2 = st.columns(2)
            with col1:
                if activa:
                    if st.session_state.ronda_actual == 0:
                        min_slider = 0
                        max_slider = info['pot_max']
                        ayuda_slider = "Primera ronda: ¡Elige tu potencia inicial libremente!"
                    else:
                        min_slider = int(max(0, pot_anterior - info['max_cambio']))
                        max_slider = int(min(info['pot_max'], pot_anterior + info['max_cambio']))
                        ayuda_slider = f"Potencia previa: {pot_anterior} MW. Cambio máx: ±{info['max_cambio']} MW"
                    
                    potencia = st.slider(f"Potencia {tech} (MW)", 
                                         min_value=min_slider, max_value=max_slider, 
                                         value=int(pot_anterior) if (st.session_state.ronda_actual > 0 and pot_anterior >= min_slider) else min_slider, 
                                         step=10, help=ayuda_slider, disabled=st.session_state.mercado_casado,
                                         key=f"pot_{equipo}_{tech}_{ronda}")
                else:
                    st.error(f"🛑 {tech} APAGADA (0 MW).")
                    potencia = 0

            with col2:
                precio = st.number_input(f"Precio {tech} (€/MWh)", min_value=-500.0, value=float(info['coste_op']),
                                         disabled=(not activa or st.session_state.mercado_casado), key=f"pre_{equipo}_{tech}_{ronda}")
            
            ofertas.append({
                "Equipo": equipo, "Tecnología": tech, "Potencia Ofertada (MW)": potencia, 
                "Precio (€/MWh)": precio, "Coste Op (€/MWh)": info['coste_op'], 
                "Coste Cambio (€/MW)": info['coste_cambio'], "Coste P/A Fijo (€)": info['coste_pa'],
                "Potencia Anterior (MW)": pot_anterior
            })
        st.divider()

# --- BOTONES DE ACCIÓN Y MOTOR DEL JUEGO ---
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("🚀 Casar Mercado", type="primary", disabled=st.session_state.mercado_casado):
        if not ofertas:
            st.warning("No hay ninguna oferta introducida.")
        else:
            df = pd.DataFrame(ofertas)
            
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
            
            if st.session_state.ronda_actual == 0:
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

            # Comprobación de Apagón
            total_asignado = df["Potencia Asignada (MW)"].sum()
            hubo_apagon = total_asignado < demanda_residual

            for index, row in df.iterrows():
                clave = f"{row['Equipo']}_{row['Tecnología']}"
                st.session_state.potencia_asignada_anterior[clave] = row["Potencia Asignada (MW)"]
                st.session_state.dinero_acumulado[row['Equipo']] += row["Beneficio Neto (€)"]
                # NUEVO: Sumamos la energía a la memoria general del equipo
                st.session_state.energia_acumulada[row['Equipo']][row['Tecnología']] += row["Potencia Asignada (MW)"]

            # Aplicar Multa del Apagón si ocurre
            if hubo_apagon:
                st.session_state.hubo_apagon = True
                for eq in st.session_state.dinero_acumulado.keys():
                    multa = abs(st.session_state.dinero_acumulado[eq]) * 0.33
                    st.session_state.penalizacion_apagon[eq] = multa
                    st.session_state.dinero_acumulado[eq] -= multa
            else:
                st.session_state.hubo_apagon = False
                st.session_state.penalizacion_apagon = {}
            
            st.session_state.mercado_casado = True
            st.session_state.resultados_df = df
            st.session_state.precio_marginal = precio_marginal
            st.rerun()

with col_btn2:
    if st.session_state.mercado_casado:
        if st.button("⏭️ Siguiente Hora", type="primary"):
            st.session_state.ronda_actual += 1
            st.session_state.mercado_casado = False
            st.session_state.hubo_apagon = False
            st.session_state.penalizacion_apagon = {}
            st.rerun()

# --- MOSTRAR RESULTADOS ---
if st.session_state.mercado_casado:
    
    # ALERTA DE APAGÓN
    if st.session_state.hubo_apagon:
        st.error("### 🌑⚠️ ¡APAGÓN GLOBAL! ⚠️🌑\n**No se ha conseguido cubrir la demanda residual. El sistema eléctrico ha colapsado y todos los jugadores han sido penalizados perdiendo un 33% de su saldo actual.**")

    st.success(f"### 💰 Precio Final del Mercado: {st.session_state.precio_marginal:,.2f} €/MWh")
    
    st.subheader("🎮 Resumen de la Ronda")
    df_res = st.session_state.resultados_df
    
    resumen_beneficios = df_res.groupby("Equipo")["Beneficio Neto (€)"].sum().reset_index()
    max_beneficio = resumen_beneficios["Beneficio Neto (€)"].max()
    
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    cols = [c1, c2, c3, c4]
    
    equipos_todos = ["Equipo 1", "Equipo 2", "Equipo 3", "Equipo 4"]
    
    for i, equipo_nombre in enumerate(equipos_todos):
        datos_equipo = df_res[df_res["Equipo"] == equipo_nombre]
        beneficio_total = datos_equipo["Beneficio Neto (€)"].sum() if not datos_equipo.empty else 0
        
        saldo_actual = st.session_state.dinero_acumulado[equipo_nombre]
        multa_apagon = st.session_state.penalizacion_apagon.get(equipo_nombre, 0)
        saldo_antes_apagon = saldo_actual + multa_apagon
        saldo_anterior = saldo_antes_apagon - beneficio_total
        
        with cols[i]:
            with st.container(border=True):
                html_content = f"<h3 style='margin-bottom: 5px;'>🛡️ {equipo_nombre}</h3>"
                html_content += f"<b>🏦 SALDO ANTERIOR:</b> {saldo_anterior:,.0f} €<br><br>"
                
                for _, row in datos_equipo.iterrows():
                    if row["Ingresos (€)"] > 0:
                        html_content += f"<span style='color: #28a745;'>🟩 <b>INGRESO {row['Tecnología'].upper()}:</b> ({row['Potencia Asignada (MW)']} MW * {st.session_state.precio_marginal:,.0f} €) = <b>+{row['Ingresos (€)']:,.0f} €</b></span><br>"
                
                for _, row in datos_equipo.iterrows():
                    if row["Costes Op (€)"] > 0:
                        html_content += f"<span style='color: #fd7e14;'>🟧 <b>COSTE OP. {row['Tecnología'].upper()}:</b> <b>-{row['Costes Op (€)']:,.0f} €</b></span><br>"
                        
                for _, row in datos_equipo.iterrows():
                    if row["Penalización Cambio (€)"] > 0:
                        html_content += f"<span style='color: #dc3545;'>📉 <b>CAMBIO POTENCIA {row['Tecnología'].upper()}:</b> <b>-{row['Penalización Cambio (€)']:,.0f} €</b></span><br>"
                    if row["Penalización Parada/Arranque (€)"] > 0:
                        accion = "ARRANQUE" if row["Potencia Anterior (MW)"] == 0 else "CIERRE"
                        html_content += f"<span style='color: #dc3545;'>🚨 <b>{accion} DE {row['Tecnología'].upper()}:</b> <b>-{row['Penalización Parada/Arranque (€)']:,.0f} €</b></span><br>"
                        
                html_content += "<hr style='margin: 10px 0; border-color: #555;'>"
                
                if beneficio_total == max_beneficio and max_beneficio > 0:
                    arcoiris = "background-image: linear-gradient(to right, #ff3333, #ff9933, #cccc00, #33cc33, #3399ff, #9933ff); -webkit-background-clip: text; color: transparent;"
                    html_content += f"<span style='{arcoiris} font-size: 1.25em; font-weight: bold;'>🌈 BENEFICIO RONDA: {beneficio_total:,.0f} € 🏆</span><br>"
                else:
                    html_content += f"<b>📊 BENEFICIO RONDA:</b> {beneficio_total:,.0f} €<br>"
                
                if st.session_state.hubo_apagon:
                    html_content += f"<br><span style='color: #dc3545; font-size: 1.1em; font-weight: bold;'>🌑 MULTA POR APAGÓN (33%): -{multa_apagon:,.0f} €</span><br>"
                    
                html_content += f"<br><span style='color: #FFD700; font-size: 1.5em; font-weight: bold; text-shadow: 1px 1px 2px #000000;'>💰 SALDO FINAL: {saldo_actual:,.0f} €</span>"
                
                st.markdown(html_content, unsafe_allow_html=True)

    # --- TABLA DE DETALLES ---
    st.divider()
    with st.expander("Ver tabla de Detalles y Merit Order"):
        columnas_mostrar = ["Equipo", "Tecnología", "Potencia Ofertada (MW)", "Potencia Asignada (MW)", "Penalización Cambio (€)", "Penalización Parada/Arranque (€)", "Beneficio Neto (€)"]
        st.dataframe(df_res[columnas_mostrar], use_container_width=True)