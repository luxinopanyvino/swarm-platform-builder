"""Compose dev/prod separados, TLS y cabeceras + CSP (SPEC-017 / T3.4 / AC4).

AC4: existen compose **dev y prod separados** (prod sin `--reload` ni `DEBUG`) y
nginx sirve con TLS y cabeceras de seguridad + CSP.

La CSP se comprobó además **cargando la aplicación construida en Chromium con estas
cabeceras puestas**, que es como se descubrió que `ds/colors_and_type.css` importa
Google Fonts en runtime: no aparece en `index.html`, así que solo lo delata el
navegador. Aquí queda fijado para que nadie la recorte sin volver a comprobarlo.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

COMPOSE_DEV = REPO_DIR / "docker-compose.yml"
COMPOSE_PROD = REPO_DIR / "docker-compose.prod.yml"
NGINX_DEV = REPO_DIR / "frontend" / "nginx.conf"
NGINX_PROD = REPO_DIR / "frontend" / "nginx.prod.conf"
HEADERS_INC = REPO_DIR / "frontend" / "security-headers.inc"


class _Tolerante(yaml.SafeLoader):
    """Compose usa etiquetas `!override`/`!reset` que SafeLoader no conoce."""


_Tolerante.add_multi_constructor("!", lambda loader, suffix, node: _resolver(loader, node))


def _resolver(loader, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    return loader.construct_scalar(node)


def _load(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Tolerante)


def _csp() -> dict[str, list[str]]:
    """La CSP como diccionario directiva → orígenes."""
    texto = HEADERS_INC.read_text(encoding="utf-8")
    valor = re.search(r'add_header\s+Content-Security-Policy\s+"([^"]+)"', texto).group(1)
    politica = {}
    for trozo in valor.split(";"):
        partes = trozo.split()
        if partes:
            politica[partes[0]] = partes[1:]
    return politica


# --------------------------------------------------------------------------- #
# AC4 — dev y prod separados
# --------------------------------------------------------------------------- #

def test_there_is_a_separate_production_override():
    assert COMPOSE_PROD.exists(), "AC4 exige un compose de producción separado"


def test_production_drops_the_reload_flag():
    """`--reload` en producción es un vigilante de ficheros y un riesgo de reinicio."""
    comando = _load(COMPOSE_PROD)["services"]["backend"]["command"]
    assert "--reload" not in " ".join(comando) if isinstance(comando, list) else "--reload" not in comando
    # Y el de desarrollo sí lo lleva: así se ve que el override cambia algo.
    assert "--reload" in _load(COMPOSE_DEV)["services"]["backend"]["command"]


def test_production_disables_debug_and_dev_role_promotion():
    entorno = _load(COMPOSE_PROD)["services"]["backend"]["environment"]
    assert entorno["DEBUG"] == "false"
    assert entorno["ENABLE_DEV_ROLE_PROMOTION"] == "false"


def test_production_stops_mounting_the_host_source_tree():
    """La imagen deja de ser inmutable si el código sigue viniendo del host —y desde
    T3.3 el proceso no root tampoco podría escribir en esas rutas."""
    montajes = [str(v) for v in _load(COMPOSE_PROD)["services"]["backend"]["volumes"]]
    assert not any(v.startswith("./backend:") for v in montajes), (
        f"el código sigue montado desde el host: {montajes}"
    )


def test_production_keeps_the_persistent_volumes():
    """Quitar el bind mount no puede llevarse por delante lo que debe persistir."""
    montajes = " ".join(str(v) for v in _load(COMPOSE_PROD)["services"]["backend"]["volumes"])
    for ruta in ("/app/app/.rag_local", "/app/app/.assets", "/app/logs"):
        assert ruta in montajes, f"{ruta} dejaría de persistir en producción"


def test_production_stops_publishing_the_backend_port():
    """Solo se llega al backend por la pasarela; publicarlo lo deja al descubierto."""
    assert not _load(COMPOSE_PROD)["services"]["backend"].get("ports")


def test_production_serves_tls_on_the_published_https_port():
    puertos = [str(p) for p in _load(COMPOSE_PROD)["services"]["frontend"]["ports"]]
    assert any(p.startswith("443:") for p in puertos), f"sin HTTPS publicado: {puertos}"


def test_production_mounts_its_own_nginx_config_and_certificates():
    montajes = " ".join(str(v) for v in _load(COMPOSE_PROD)["services"]["frontend"]["volumes"])
    assert "nginx.prod.conf" in montajes
    assert "/etc/nginx/certs" in montajes


# --------------------------------------------------------------------------- #
# AC4 — TLS
# --------------------------------------------------------------------------- #

def test_the_production_config_terminates_tls():
    conf = NGINX_PROD.read_text(encoding="utf-8")
    assert re.search(r"listen\s+\d+\s+ssl", conf), "ningún listen con ssl"
    assert "ssl_certificate" in conf and "ssl_certificate_key" in conf


def test_plain_http_redirects_instead_of_serving():
    conf = NGINX_PROD.read_text(encoding="utf-8")
    assert re.search(r"return\s+301\s+https://", conf), "el HTTP no redirige a HTTPS"


def test_only_modern_tls_versions_are_accepted():
    protocolos = re.search(r"ssl_protocols\s+([^;]+);", NGINX_PROD.read_text(encoding="utf-8")).group(1)
    assert "TLSv1.2" in protocolos and "TLSv1.3" in protocolos
    assert "TLSv1.1" not in protocolos and "SSLv3" not in protocolos


def test_hsts_is_sent_in_production_only():
    """Enviar HSTS por HTTP dejaría el navegador incapaz de volver a abrir el sitio."""
    assert "Strict-Transport-Security" in NGINX_PROD.read_text(encoding="utf-8")
    assert "Strict-Transport-Security" not in NGINX_DEV.read_text(encoding="utf-8")


def test_private_keys_can_never_be_committed():
    ignorados = (REPO_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "certs/*.pem" in ignorados


# --------------------------------------------------------------------------- #
# AC4 — cabeceras de seguridad
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cabecera", [
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Content-Security-Policy",
])
def test_the_security_headers_are_declared(cabecera):
    assert cabecera in HEADERS_INC.read_text(encoding="utf-8")


def test_dev_and_prod_share_the_same_headers_file():
    """Una CSP que solo se aplica en producción se descubre rota en producción."""
    for conf in (NGINX_DEV, NGINX_PROD):
        assert "security-headers.inc" in conf.read_text(encoding="utf-8")


def test_the_headers_are_marked_always():
    """Sin `always`, nginx no las envía en respuestas de error —que son las que
    más falta hace proteger."""
    for linea in HEADERS_INC.read_text(encoding="utf-8").splitlines():
        if linea.strip().startswith("add_header"):
            assert linea.rstrip().endswith("always;"), linea


# --------------------------------------------------------------------------- #
# AC4 — la CSP, verificada contra la aplicación real
# --------------------------------------------------------------------------- #

def test_scripts_are_restricted_to_the_same_origin():
    """La directiva que de verdad para un XSS. El build de Vite no emite scripts en
    línea, así que no hay excusa para 'unsafe-inline' aquí."""
    script_src = _csp()["script-src"]
    assert script_src == ["'self'"], f"script-src relajado: {script_src}"
    assert "'unsafe-eval'" not in script_src


def test_the_paper_layout_still_works_under_the_policy():
    """La maqueta lleva su CSS en un <style> en línea y sus figuras como data URI
    (SPEC-022/T11.5). Sin estos dos permisos, el paper sale sin estilo y sin
    imágenes — comprobado en Chromium."""
    politica = _csp()
    assert "'unsafe-inline'" in politica["style-src"]
    assert "data:" in politica["img-src"]


def test_the_fonts_the_app_actually_loads_are_allowed():
    """`ds/colors_and_type.css` importa Google Fonts en runtime.

    No aparece en index.html: se descubrió cargando la aplicación con la CSP
    puesta. Hacen falta los dos dominios —googleapis sirve el CSS y gstatic los
    ficheros de fuente—; con uno solo se carga la hoja y ninguna fuente.
    """
    politica = _csp()
    assert any("fonts.googleapis.com" in o for o in politica["style-src"])
    assert any("fonts.gstatic.com" in o for o in politica["font-src"])


@pytest.mark.parametrize("directiva,esperado", [
    ("object-src", "'none'"),
    ("base-uri", "'self'"),
    ("form-action", "'self'"),
    ("frame-ancestors", "'none'"),
])
def test_the_policy_closes_the_usual_holes(directiva, esperado):
    assert _csp()[directiva] == [esperado]


def test_the_api_is_reachable_from_the_same_origin_only():
    """La pasarela existe justamente para poder ser así de estricto."""
    assert _csp()["connect-src"] == ["'self'"]


# --------------------------------------------------------------------------- #
# La pasarela
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("conf", [NGINX_DEV, NGINX_PROD])
def test_nginx_proxies_the_api(conf):
    texto = conf.read_text(encoding="utf-8")
    assert "location /api/" in texto
    assert "proxy_pass http://backend:8000" in texto


@pytest.mark.parametrize("conf", [NGINX_DEV, NGINX_PROD])
def test_sse_is_not_buffered(conf):
    """El pipeline emite por streaming: con búfer, la ejecución parece congelada."""
    assert "proxy_buffering off" in conf.read_text(encoding="utf-8")


@pytest.mark.parametrize("conf", [NGINX_DEV, NGINX_PROD])
def test_the_correlation_header_survives_the_proxy(conf):
    """Sin ella se pierde el request_id de T5.1 y el audit log deja de cruzarse."""
    assert "X-Request-ID" in conf.read_text(encoding="utf-8")


def test_the_frontend_is_built_for_same_origin_calls():
    """`VITE_API_URL` vacío ⇒ rutas relativas. Con un origen absoluto, `connect-src
    'self'` bloquearía todas las llamadas a la API."""
    for compose in (COMPOSE_DEV, COMPOSE_PROD):
        args = _load(compose)["services"]["frontend"].get("build", {}).get("args", [])
        for arg in args:
            if str(arg).startswith("VITE_API_URL"):
                assert str(arg).strip() in ("VITE_API_URL=", "VITE_API_URL"), (
                    f"{compose.name}: {arg} rompería connect-src 'self'"
                )
