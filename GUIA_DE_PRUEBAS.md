# Guía de Pruebas Manuales · SOC-Lite Platform

Esta guía paso a paso te permitirá validar y poner a prueba cada módulo y funcionalidad de **SOC-Lite**, verificando su comportamiento funcional, responsivo y de seguridad.

---

## 1. Accesos y Credenciales de Prueba

* **URL del Sistema (Frontend):** [http://localhost:8080](http://localhost:8080)
* **Documentación API (Swagger Backend):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Contraseña común para todas las cuentas:** `SocLite#2026!`

| Rol | Correo Demo | Alcance y Permisos |
| :--- | :--- | :--- |
| **Analista SOC** | `analista1@soclite.local` | Triaje, investigación, validación humana y escalamiento |
| **Auditor** | `auditor@soclite.local` | Consulta y verificación criptográfica de la bitácora de auditoría |
| **Administrador** | `admin@soclite.local` | Gestión completa de usuarios, roles, métricas y reportes |
| **Jefe de SOC** | `gerente.soc@soclite.local` | Supervisión de SLAs, reportes de gestión y métricas |

---

## 2. Casos de Prueba Paso a Paso

### Prueba 1: Autenticación, Selector Rápido de Cuentas y Control de Acceso (RBAC)
1. Ingresa a [http://localhost:8080](http://localhost:8080).
2. **Selector Rápido de Demostración:**
   * En la pantalla de inicio de sesión observarás las **tarjetas de selección rápida** (Analista SOC, Auditor, Administrador, Jefe de SOC).
   * Haz un clic sobre la tarjeta de **Analista SOC (María Quispe)**.
   * **Verificación:** Observa cómo el correo `analista1@soclite.local` y la contraseña `SocLite#2026!` se **autocompletan instantáneamente**, resaltando la tarjeta seleccionada con un anillo azul y checkmark.
   * Puedes hacer clic en **Auditor** o **Administrador** para cambiar de cuenta inmediatamente con un solo toque.
3. Presiona el botón **Entrar a SOC-Lite**:
   * El sistema ingresa al **Dashboard** renovado con la paleta de colores del UI Kit (azul eléctrico, fondo blanco puro, tarjetas redondeadas y acentos en turquesa y coral).
   * En la barra superior observarás el título *Overview*, el buscador redondeado, botones circulares de notificación y configuración, y el avatar del usuario.
   * En el menú lateral se activa el indicador vertical azul del ítem activo.
   * Al iniciar como Analista, las opciones de "Usuarios y roles" y "Auditoría" quedan restringidas según su rol RBAC.
4. Para probar otro rol, haz clic en **Cerrar sesión** en la esquina inferior del menú lateral y selecciona otra tarjeta (ej. Administrador).

---

### Prueba 2: Módulo de Alertas (Filtros y Resolución del Error 500)
1. Con la sesión iniciada, dirígete a **Alertas** en el menú lateral.
2. **Verificación esperada:**
   * La lista de alertas carga limpiamente (24 alertas precargadas).
   * **No aparece** ningún cartel de *"Error interno del servidor"* (HTTP 500 corregido).
3. **Filtros interactivos:**
   * En el selector **Severidad**, elige `critical` y pulsa **Aplicar**. Comprueba que solo liste alertas críticas.
   * En el buscador escribe `phishing` o `brute force` y presiona Enter. Verifica el filtrado en vivo.
   * Presiona la **X** en el buscador para limpiar y volver a la vista general.

---

### Prueba 3: Triaje Asistido por Inteligencia Artificial (Ollama + Llama 3.1)
1. En la lista de alertas, haz clic en el título de una alerta (ej. *"Correo de phishing reportado por usuario"* o *"Múltiples intentos de autenticación SSH fallidos"*).
2. En la vista de detalle:
   * Revisa la columna derecha: **Triaje asistido por IA**.
   * Observa el veredicto (ej. `Verdadero positivo` o `Sospechoso`), la confianza (ej. `92%`), el resumen estructurado y las **Acciones recomendadas** (ej. bloquear IP, revocar sesiones).
3. **Re-ejecutar triaje:**
   * Haz clic en el botón superior **Re-ejecutar triaje**.
   * Espera unos segundos mientras Ollama procesa la inferencia en local.
   * **Verificación:** Debe aparecer una notificación de confirmación verde y los datos se actualizarán.
4. **Validación humana (Human-in-the-Loop):**
   * En la sección inferior *"Validación del triaje (revisión humana)"*, selecciona un veredicto (ej. `Verdadero positivo`).
   * Escribe un comentario de al menos 5 caracteres (ej. *"Se confirma IP maliciosa según IOCs"*).
   * Haz clic en **Registrar veredicto**.
   * **Verificación:** Se actualiza el veredicto humano y queda auditado en el sistema.

---

### Prueba 4: Escalamiento y Gestión de Incidentes
1. Estando dentro del detalle de una alerta crítica o alta, haz clic en el botón **Escalar a incidente**.
2. **Verificación:** El sistema mostrará un aviso indicando que el incidente (ej. `INC-2026-000X`) ha sido creado.
3. Ve a la pestaña **Incidentes** en el menú lateral:
   * Comprueba que figure el nuevo incidente con su código, título y estado `Abierto`.
   * Observa la fecha límite de **SLA** calculada automáticamente.
   * En el selector de estado, puedes cambiarlo a `En investigación`, `Contenido` o presionar **Cerrar** para resolver el incidente.

---

### Prueba 5: Módulo de Reportes Ejecutivos (Nuevo Diseño PDF)
1. Dirígete a la pestaña **Reportes**.
2. En el panel izquierdo *"Generar reporte"*:
   * **Título:** Escribe `Reporte Operacional de Prueba`.
   * **Tipo:** Selecciona `Operacional` o `Gestión`.
   * **Formato:** Selecciona `PDF` (también puedes probar `Word` y `Excel`).
   * **Fechas:** Deja el rango de los últimos 7 días o selecciona un rango que incluya las alertas.
   * Haz clic en **Generar reporte**.
3. En la tabla de historial a la derecha, ubica el reporte recién creado y haz clic en **Descargar**.
4. Abre el archivo PDF generado en tu visor o navegador y valida las siguientes mejoras visuales:
   * **Encabezado institucional:** Banner azul marino (*SOC-Lite · Security Operations Center*) con clasificación *CONFIDENCIAL · ISO/IEC 27001*.
   * **Dashboard de KPIs:** Tarjetas métricas superiores con Total de Alertas, % Triaje Automático, Falsos Positivos y Cumplimiento de SLA.
   * **Tablas ejecutivas:** Distribución por severidad con etiquetas coloreadas y Top Reglas SIEM.
   * **Numeración y pie de página:** Indicador *"Página X de Y"* en todas las páginas y nota de trazabilidad criptográfica SHA-256.

---

### Prueba 6: Módulo de Auditoría (Verificación SHA-256 y Corrección 500)
1. Cierra sesión e inicia como `auditor@soclite.local` (o `admin@soclite.local`).
2. Entra a la sección **Auditoría**.
3. **Verificación esperada:**
   * La bitácora carga todos los eventos históricos sin error 500.
   * Cada acción realizada en las pruebas anteriores (login, triaje, generación de reportes) aparece registrada con usuario, acción, IP y hora.
4. **Verificación Criptográfica:**
   * En la esquina superior derecha, pulsa el botón **Verificar integridad**.
   * **Verificación:** Debe mostrarse un banner verde: *"Cadena íntegra: X eventos verificados"*, comprobando que los hashes encadenados en PostgreSQL no han sido alterados ni manipulados.

---

### Prueba 7: Diseño Responsivo (Móvil y Tablet)
1. En cualquier pantalla (Dashboard, Alertas, Reportes o Auditoría), presiona la tecla `F12` en tu teclado para abrir las Herramientas de Desarrollador del navegador.
2. Haz clic en el ícono de **Dispositivos móviles** (Ctrl + Shift + M en Chrome / Edge) y selecciona dimensiones de celular (ej. *iPhone 14* o *375x667*).
3. **Verificaciones esperadas:**
   * **Menú lateral:** Se oculta automáticamente. Al presionar el botón de hamburguesa (`☰`), el menú se despliega sobre un fondo oscuro desenfocado (*backdrop*). Al tocar fuera o la `X`, se cierra limpiamente.
   * **Alertas y Auditoría:** En lugar de una tabla recortada con scroll horizontal forzado, los registros se adaptan en **tarjetas móviles compactas** con etiquetas de severidad y badges legibles.
   * **Reportes:** El formulario y el listado de reportes se apilan verticalmente, facilitando la descarga en pantallas pequeñas.

