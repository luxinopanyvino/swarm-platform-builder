# Cabeceras de seguridad comunes a dev y prod (SPEC-017 / T3.4 / AC4).
#
# Cada valor está aquí por un motivo concreto; si alguno estorba, cámbialo con el
# motivo delante, no lo borres.

# La aplicación no debe embeberse en un marco ajeno (clickjacking).
add_header X-Frame-Options "DENY" always;
# No adivinar tipos: un fichero servido como texto no debe ejecutarse como script.
add_header X-Content-Type-Options "nosniff" always;
# No filtrar la ruta del artículo al navegar a un enlace externo.
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
# La plataforma no usa cámara, micrófono ni geolocalización.
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

# ── Content-Security-Policy ──────────────────────────────────────────────────
#
#  default-src 'self'   Todo del mismo origen salvo lo que se abre abajo.
#  script-src  'self'   El build de Vite no emite scripts en línea (comprobado
#                       sobre dist/index.html), así que no hace falta 'unsafe-inline'
#                       ni nonces: es la directiva que de verdad para un XSS.
#  style-src   … 'unsafe-inline' fonts.googleapis.com
#                       'unsafe-inline' es obligado, y conviene saber por qué: la
#                       interfaz usa `style={{…}}` de React por todas partes
#                       (atributos de estilo) y la maqueta del paper lleva su CSS
#                       en un <style> en línea. Quitarlo dejaría la aplicación sin
#                       estilos.
#                       El dominio de Google Fonts está porque `ds/colors_and_type.css`
#                       hace `@import url(fonts.googleapis.com…)` para Source Serif 4,
#                       Source Sans 3 y JetBrains Mono. Se descubrió cargando la
#                       aplicación con esta CSP puesta: el `@import` no aparece en
#                       index.html, así que solo lo delata el navegador.
#  font-src    … fonts.gstatic.com
#                       Google Fonts sirve el CSS desde googleapis y los ficheros
#                       de fuente desde gstatic: hacen falta los dos o se cargaría
#                       la hoja y ninguna fuente.
#  img-src     'self' data: blob:
#                       Las figuras de los artículos se incrustan como data URI
#                       (SPEC-022/T11.5) para que el HTML del paper sea
#                       autocontenido e imprimible sin peticiones extra.
#  connect-src 'self'   API y SSE van por el mismo origen gracias a la pasarela.
#  frame-src   'self'   La vista de maquetación usa un iframe `srcdoc`; su
#                       aislamiento real lo da el atributo `sandbox` de
#                       SPEC-016/AC1, esto es la segunda capa.
#  object-src  'none'   Sin Flash, sin applets, sin sorpresas.
#  base-uri    'self'   Impide que un <base> inyectado reescriba las rutas.
#  form-action 'self'   Un formulario inyectado no puede enviar a otro sitio.
#  frame-ancestors 'none'
#                       Equivalente moderno de X-Frame-Options, para navegadores
#                       que ya no miran aquella.
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'" always;
