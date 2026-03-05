import streamlit as st
import pandas as pd

# streamlit run SimuladorEquipos.py

st.set_page_config(page_title="Simulador Mercado Eléctrico", layout="wide")

# --- NUEVO: FUNCIÓN PARA LA VENTANA EMERGENTE (MODAL) ---
@st.dialog("📊 Ficha Técnica de las Centrales", width="large")
def mostrar_ficha_tecnica():
    st.markdown("Consulta aquí los parámetros de tu equipo:")
    
    # Recuperamos los textos originales más largos para que se vea perfecto en grande
    datos_tecnicos = {
        "Parámetro": [
            "Potencia Máx. (MW)",
            "Cambio Máx. por Hora (MW)",
            "Coste Operativo (€/MWh)",
            "Coste por Cambio (€/MW)",
            "Coste Parada/Arranque (€)"
        ]
    }
    
    for tech, info in st.session_state.TECNOLOGIAS.items():
        datos_tecnicos[tech] = [
            f"{info['pot_max']:,.0f}",
            f"{info['max_cambio']:,.0f}" if info['max_cambio'] < info['pot_max'] else "Sin límite",
            f"{info['coste_op']:,.2f}",
            f"{info['coste_cambio']:,.0f}",
            f"{info['coste_pa']:,.0f}"
        ]
    
    df_tecnico = pd.DataFrame(datos_tecnicos)
    styled_df_tec = df_tecnico.style.apply(
        lambda x: ['font-weight: bold; border-right: 2px solid #9ca3af;' if x.name == 'Parámetro' else '' for _ in x]
    )
    
    st.dataframe(styled_df_tec, hide_index=True, use_container_width=True)
# ---------------------------------------------------------

# --- PANTALLA DE INICIO Y CONFIGURACIÓN ---
if 'juego_iniciado' not in st.session_state:
    st.session_state.juego_iniciado = False
    st.session_state.ronda_actual = 0
    st.session_state.mercado_casado = False
    st.session_state.hubo_apagon = False
    st.session_state.penalizacion_apagon = {}
    st.session_state.potencia_asignada_anterior = {} 

if not st.session_state.juego_iniciado:
    st.title("⚡ Configuración de la Partida")
    st.markdown("### Bienvenido al Simulador del Mercado Eléctrico")
    st.info("Selecciona el número de equipos que van a participar. El juego ajustará automáticamente el tamaño de las centrales para que el mercado esté equilibrado.")
    
    num_equipos = st.selectbox("Número de equipos:", [2, 3, 4, 5], index=2) # Por defecto 4
    
    if st.button("🚀 Comenzar Partida", type="primary"):
        st.session_state.num_equipos = num_equipos
        st.session_state.juego_iniciado = True
        
        # Ajuste dinámico de potencia: El mercado base era para 4 jugadores.
        # Factor = 4 / num_jugadores. Si juegan 2, tienen el doble de potencia cada uno.
        factor = 4 / num_equipos
        
        st.session_state.TECNOLOGIAS = {
            "Nuclear": {"pot_max": int(970 * factor), "coste_op": 8.0, "max_cambio": int(100 * factor), "coste_cambio": 70, "coste_pa": 150000},
            "Carbón": {"pot_max": int(830 * factor), "coste_op": 86.0, "max_cambio": int(200 * factor), "coste_cambio": 50, "coste_pa": 70000},
            "Ciclo Combinado": {"pot_max": int(800 * factor), "coste_op": 121.0, "max_cambio": int(400 * factor), "coste_cambio": 30, "coste_pa": 10000},
            "Gas": {"pot_max": int(500 * factor), "coste_op": 168.0, "max_cambio": int(500 * factor), "coste_cambio": 0, "coste_pa": 0}
        }
        
        # Inicializar equipos en base al número elegido
        st.session_state.equipos_nombres = [f"Equipo {i+1}" for i in range(num_equipos)]
        st.session_state.dinero_acumulado = {eq: 500000 for eq in st.session_state.equipos_nombres}
        st.session_state.energia_acumulada = {
            eq: {tech: 0 for tech in st.session_state.TECNOLOGIAS.keys()} for eq in st.session_state.equipos_nombres
        }
        st.rerun()
    st.stop() # Detenemos aquí la ejecución hasta que le den a Comenzar

# --- COMIENZA EL JUEGO REAL ---
st.title("⚡ Simulador de Mercado Eléctrico")

HORARIOS = [
    {"hora": "08:00 - 09:00", "demanda": 8790, "renovables": 4900},
    {"hora": "09:00 - 10:00", "demanda": 9271, "renovables": 6600},
    {"hora": "10:00 - 11:00", "demanda": 9700, "renovables": 8800},
    {"hora": "11:00 - 12:00", "demanda": 9100, "renovables": 4100},
    {"hora": "12:00 - 13:00", "demanda": 8750, "renovables": 2750},
]

ronda = st.session_state.ronda_actual

# --- FINAL DEL JUEGO ---
if ronda >= len(HORARIOS):
    st.success("🎉 ¡La jornada ha terminado! Aquí tenéis los resultados finales.")
    st.balloons()
    
    st.divider()
    st.markdown("<h1 style='text-align: center;'>🏆 CLASIFICACIÓN FINAL 🏆</h1>", unsafe_allow_html=True)
    
    clasificacion = sorted(st.session_state.dinero_acumulado.items(), key=lambda x: x[1], reverse=True)
    # Dibujamos tantas columnas como equipos haya
    cols_lb = st.columns(st.session_state.num_equipos) 
    medallas = ["🥇 1º PUESTO", "🥈 2º PUESTO", "🥉 3º PUESTO", "🏅 4º PUESTO", "🏅 5º PUESTO"]
    
    for i, (equipo_lb, saldo_lb) in enumerate(clasificacion):
        with cols_lb[i]:
            with st.container(border=True):
                st.markdown(f"<h3 style='text-align: center;'>{medallas[i]}</h3>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='text-align: center;'>{equipo_lb}</h4>", unsafe_allow_html=True)
                
                # Dinero
                color = "#28a745" if saldo_lb >= 0 else "#dc3545"
                st.markdown(f"<h2 style='text-align: center; color: {color};'>{saldo_lb:,.0f} €</h2>", unsafe_allow_html=True)
                
                # Estadísticas de energía
                st.divider()
                datos_energia = st.session_state.energia_acumulada[equipo_lb]
                energia_total = sum(datos_energia.values())
                
                st.markdown(f"<p style='text-align: center; font-size: 1.1em;'><b>⚡ Energía Suministrada:</b><br>{energia_total:,.0f} MWh</p>", unsafe_allow_html=True)
                
                tech_ordenadas = sorted(datos_energia.items(), key=lambda x: x[1], reverse=True)
                html_techs = "<div style='font-size: 0.9em; padding-left: 10px;'>"
                posicion = 1
                for tech, mwh in tech_ordenadas:
                    if mwh > 0:
                        porcentaje = (mwh / energia_total * 100) if energia_total > 0 else 0
                        html_techs += f"<b>{posicion}º {tech}:</b> {mwh:,.0f} MWh <i>({porcentaje:.1f}%)</i><br>"
                        posicion += 1
                
                if energia_total == 0:
                    html_techs += "<i>No generó energía</i>"
                html_techs += "</div><br>"
                
                st.markdown(html_techs, unsafe_allow_html=True)
    
    st.stop()

# --- CÓDIGO NORMAL DE LA RONDA ---
datos_hora = HORARIOS[ronda]
hora_str = datos_hora["hora"]
demanda_residual = datos_hora["demanda"] - datos_hora["renovables"]

# --- PANEL SUPERIOR (BARRA LATERAL) ---
st.sidebar.header(f"🕒 HORA ACTUAL: {hora_str}")
st.sidebar.progress((ronda + 1) / len(HORARIOS), text=f"Ronda {ronda + 1} de {len(HORARIOS)}")
st.sidebar.info(f"**Demanda Total:** {datos_hora['demanda']} MW\n\n**Renovables:** -{datos_hora['renovables']} MW\n\n---\n**🏭 DEMANDA A CUBRIR:** {demanda_residual} MW")

st.sidebar.divider()

# --- BOTÓN QUE ABRE LA VENTANA EMERGENTE ---
if st.sidebar.button("🔍 Abrir Ficha Técnica", type="primary", use_container_width=True):
    mostrar_ficha_tecnica()

# --- INTERFAZ DE OFERTAS ---
st.subheader(f"📝 Ofertas para el tramo {hora_str}")

tabs = st.tabs(st.session_state.equipos_nombres)
ofertas = []


for i, tab in enumerate(tabs):
    equipo = st.session_state.equipos_nombres[i]
    with tab:
        for tech, info in st.session_state.TECNOLOGIAS.items():
            clave_historial = f"{equipo}_{tech}"
            pot_anterior = st.session_state.potencia_asignada_anterior.get(clave_historial, 0)
            
            # EL INTERRUPTOR EMPIEZA APAGADO EN LA RONDA 0
            activa = st.toggle(f"🔌🔋 Activar {tech}", value=(pot_anterior > 0), key=f"tgl_{equipo}_{tech}_{ronda}", disabled=st.session_state.mercado_casado)
            
            col1, col2 = st.columns(2)
            with col1:
                if activa:
                    if st.session_state.ronda_actual == 0:
                        min_slider = 0
                        max_slider = info['pot_max']
                        ayuda_slider = f"Primera ronda: ¡Elige hasta {max_slider} MW!"
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
                    st.error(f"🚫🪫 {tech} APAGADA (0 MW).")
                    potencia = 0

            with col2:
                # PRECIO SUBE DE 1 EN 1 EURO
                precio = st.number_input(f"Precio {tech} (€/MWh)", min_value=-500.0, value=float(info['coste_op']),
                                         step=1.0,
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
    if st.button("💹 Casar Mercado", type="primary", disabled=st.session_state.mercado_casado):
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

            total_asignado = df["Potencia Asignada (MW)"].sum()
            hubo_apagon = total_asignado < demanda_residual

            if hubo_apagon:
                st.session_state.hubo_apagon = True
                # IMPORTANTE: No actualizamos el dinero ni la energía porque la ronda es nula
            else:
                st.session_state.hubo_apagon = False
                # Solo guardamos saldos e historial si el mercado casa con éxito
                for index, row in df.iterrows():
                    clave = f"{row['Equipo']}_{row['Tecnología']}"
                    st.session_state.potencia_asignada_anterior[clave] = row["Potencia Asignada (MW)"]
                    st.session_state.dinero_acumulado[row['Equipo']] += row["Beneficio Neto (€)"]
                    st.session_state.energia_acumulada[row['Equipo']][row['Tecnología']] += row["Potencia Asignada (MW)"]

            st.session_state.mercado_casado = True
            st.session_state.resultados_df = df
            st.session_state.precio_marginal = precio_marginal
            st.rerun()

with col_btn2:
    # Solo mostramos el botón de avanzar hora si el mercado se casó Y NO hubo apagón
    if st.session_state.mercado_casado and not st.session_state.hubo_apagon:
        if st.button("⏭️ Siguiente Hora", type="primary"):
            st.session_state.ronda_actual += 1
            st.session_state.mercado_casado = False
            st.session_state.hubo_apagon = False
            st.rerun()

# --- MOSTRAR RESULTADOS ---
if st.session_state.mercado_casado:
    
    # --- LÓGICA DE APAGÓN ---
    if st.session_state.hubo_apagon:
        st.markdown("<h1 style='text-align: center; color: #ff0000; font-size: 4em;'>🚨 ¡ALERTA APAGÓN! 🚨</h1>", unsafe_allow_html=True)
        
        potencia_ofertada_total = st.session_state.resultados_df['Potencia Ofertada (MW)'].sum()
        
        st.error(f"""
        ### **Red Eléctrica de España (REE) INFORMA:**
        No se ha logrado cubrir la demanda residual de **{demanda_residual} MW** (Solo se han ofertado {potencia_ofertada_total} MW en total).
        
        El sistema eléctrico está al borde del colapso. El mercado ha sido anulado. **Estáis obligados a rehacer las ofertas para esta misma hora.**
        """)
        
        if st.button("🔄 Rehacer Ofertas para esta hora", type="primary", use_container_width=True):
            st.session_state.mercado_casado = False
            st.session_state.hubo_apagon = False
            st.rerun()
            
        st.stop() # Detenemos el código aquí para que no muestre las tablas de beneficios ni saldos (ya que la ronda fue nula)

    # --- LÓGICA NORMAL SI NO HAY APAGÓN ---
    st.success(f"### 💰 Precio Final del Mercado: {st.session_state.precio_marginal:,.2f} €/MWh")
    
    st.subheader("Resumen de la Ronda por Equipo")

# --- MOSTRAR RESULTADOS ---
if st.session_state.mercado_casado:
    
    # --- LÓGICA DE APAGÓN ---
    if st.session_state.hubo_apagon:
        st.markdown("<h1 style='text-align: center; color: #ff0000; font-size: 4em;'>🚨 ¡ALERTA APAGÓN! 🚨</h1>", unsafe_allow_html=True)
        
        potencia_ofertada_total = st.session_state.resultados_df['Potencia Ofertada (MW)'].sum()
        
        st.error(f"""
        ### **Red Eléctrica de España (REE) INFORMA:**
        No se ha logrado cubrir la demanda residual de **{demanda_residual} MW** (Solo se han ofertado {potencia_ofertada_total} MW en total).
        
        El sistema eléctrico está al borde del colapso. El mercado ha sido anulado. **Estáis obligados a rehacer las ofertas para esta misma hora.**
        """)
        
        # Opcional: Si quieres añadir aquí el mensaje de la multa del 33%, puedes ponerlo así:
        # st.error("Además, todos los jugadores han sido penalizados perdiendo un 33% de su saldo actual.")
        
        if st.button("🔄 Rehacer Ofertas para esta hora", type="primary", use_container_width=True):
            st.session_state.mercado_casado = False
            st.session_state.hubo_apagon = False
            st.rerun()
            
        st.stop() # Detenemos el código aquí para que no muestre las tablas de beneficios

    
    # (A partir de aquí sigue tu código normal con: df_res = st.session_state.resultados_df)
    df_res = st.session_state.resultados_df
    resumen_beneficios = df_res.groupby("Equipo")["Beneficio Neto (€)"].sum().reset_index()
    max_beneficio = resumen_beneficios["Beneficio Neto (€)"].max()
    
    # Ponemos a cada equipo en formato vertical (uno debajo del otro)
    for equipo_nombre in st.session_state.equipos_nombres:
        datos_equipo = df_res[df_res["Equipo"] == equipo_nombre]
        beneficio_total = datos_equipo["Beneficio Neto (€)"].sum() if not datos_equipo.empty else 0
        
        saldo_actual = st.session_state.dinero_acumulado[equipo_nombre]
        multa_apagon = st.session_state.penalizacion_apagon.get(equipo_nombre, 0)
        saldo_antes_apagon = saldo_actual + multa_apagon
        saldo_anterior = saldo_antes_apagon - beneficio_total
        
        # Contenedor visual para separar cada equipo
        with st.container(border=True):
            st.markdown(f"### 🛡️ {equipo_nombre}")
            
            # --- CONSTRUCCIÓN DE LA TABLA FIJA (EJES INVERTIDOS Y COLORES) ---
            tecnologias_orden = ["Nuclear", "Carbón", "Ciclo Combinado", "Gas"]
            
            # Diccionario para añadir el emoji a la cabecera sin romper la lógica interna
            emojis_tech = {
                "Nuclear": "☢️ Nuclear",
                "Carbón": "🪨 Carbón ",
                "Ciclo Combinado": "💨 Ciclo Combinado ",
                "Gas": "🔥 Gas "
            }
            
            # 1. Definimos las filas (Eje Y)
            data_dict = {
                "Concepto": [
                    "Oferta - Potencia (MW)",
                    "Oferta - Precio (€/MWh)",
                    "Vendido - Potencia (MW)",
                    "Vendido - Precio (€/MWh)",
                    "Cuentas - Ingresos (€)",
                    "Cuentas - Costes Op. (€)",
                    "Cuentas - Penalizaciones (€)",
                    "Cuentas - Beneficio Neto (€)"
                ]
            }
            
            # 2. Rellenamos las columnas (Eje X) con los datos de cada tecnología
            for tech in tecnologias_orden:
                tech_display = emojis_tech[tech] # Usamos el nombre con emoji para la columna
                row_data = datos_equipo[datos_equipo["Tecnología"] == tech]
                
                if not row_data.empty:
                    r = row_data.iloc[0]
                    penalizaciones = r["Penalización Cambio (€)"] + r["Penalización Parada/Arranque (€)"]
                    
                    # Formateamos previamente a texto para que quede limpio en la tabla
                    data_dict[tech_display] = [
                        f"{r['Potencia Ofertada (MW)']:,.0f}",
                        f"{r['Precio (€/MWh)']:,.2f}",
                        f"{r['Potencia Asignada (MW)']:,.0f}",
                        f"{st.session_state.precio_marginal:,.2f}" if r["Potencia Asignada (MW)"] > 0 else "0.00",
                        f"{r['Ingresos (€)']:,.0f}",
                        f"{r['Costes Op (€)']:,.0f}",
                        f"{penalizaciones:,.0f}",
                        f"{r['Beneficio Neto (€)']:,.0f}"
                    ]
                else:
                    # Si estaba apagada, rellenamos con 0
                    data_dict[tech_display] = ["0", "0.00", "0", "0.00", "0", "0", "0", "0"]
            
            # 3. Creamos el DataFrame
            df_equipo_transposed = pd.DataFrame(data_dict)
            
            # 4. Función para aplicar los colores solicitados
            def aplicar_colores(row):
                concepto = row['Concepto']
                
                # Definimos el estilo base según la palabra clave
                if 'Oferta' in concepto:
                    # Azul claro para las ofertas
                    estilo_base = 'background-color: #dbeafe; color: #1e3a8a;' 
                elif 'Vendido' in concepto or 'Ingresos' in concepto:
                    # Verde claro para vendido e ingresos
                    estilo_base = 'background-color: #dcfce7; color: #166534;' 
                elif 'Costes' in concepto or 'Penalizaciones' in concepto:
                    # Rojo claro para costes y penalizaciones
                    estilo_base = 'background-color: #fee2e2; color: #991b1b;' 
                elif 'Beneficio Neto' in concepto:
                    # Verde fuerte para el beneficio neto
                    estilo_base = 'background-color: #16a34a; color: white; font-weight: bold; font-size: 1.05em;' 
                else:
                    estilo_base = ''
                
                # Replicamos el estilo para todas las columnas de la fila
                estilos = [estilo_base] * len(row)
                
                # Resaltamos de forma especial la columna "Concepto" (índice 0)
                if estilo_base:
                    estilos[0] = estilo_base + ' font-weight: 900; border-right: 2px solid #9ca3af;'
                else:
                    estilos[0] = 'font-weight: 900; border-right: 2px solid #9ca3af;'
                    
                return estilos
            
            # 5. Aplicamos el estilo a las celdas
            styled_df = df_equipo_transposed.style.apply(aplicar_colores, axis=1)
            
            # 6. Forzamos la cabecera para que sea NEGRITA y negra
            styled_df = styled_df.set_table_styles([
                {'selector': 'th', 'props': [('font-weight', 'bold !important'), ('color', '#000000 !important')]}
            ])
            
            st.dataframe(
                styled_df,
                hide_index=True,
                use_container_width=True
            )
            
            # Mostramos el saldo final al final del contenedor, destacado
            st.divider()
            st.markdown(f"<h3 style='text-align: right; color: #1e3a8a;'>💵 SALDO ACTUAL: {saldo_actual:,.0f} €</h3>", unsafe_allow_html=True)
