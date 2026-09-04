"""Separación builder / consumidor en el frontend (SPEC-013 / T8.6 / AC7).

AC7: el *builder* reutilizable vive en `platform/`, separado de las vistas de
consumo en `projects/`, y los dos builds de Vite siguen compilando.

La separación solo vale si es **comprobable**. Un import de `platform/` hacia
`projects/` no rompe nada visible: la aplicación sigue funcionando, y solo se
descubre el día que alguien intenta montar un segundo proyecto. El test de abajo
lo convierte en un fallo.

Lo que había: el catálogo de los cinco agentes de AlejandrIA escrito **tres
veces** —dentro de `components/flow/AgentNode.jsx` (un componente del builder),
en `ExecutionPage` y en `ArticleDetailPage`— y la entrada «Artículos» dentro del
menú del dashboard. Es el equivalente en el frontend de lo que T8.3 quitó del
motor: la pieza reutilizable conociendo por su nombre a los agentes de un
proyecto concreto. El lienzo de cualquier otro proyecto pintaba sus nodos grises
y sin descripción.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

FRONT = ROOT_DIR.parent / "frontend"
FUENTE = FRONT / "src"
PLATAFORMA = FUENTE / "platform"
PROYECTOS = FUENTE / "projects"
CATALOGO = PROYECTOS / "alejandria-magazine" / "catalog.jsx"

EXTENSIONES = (".js", ".jsx")
IMPORT = re.compile(r"""(?:from\s+|import\s*\()['"]([^'"]+)['"]""")


def _ficheros(raiz: Path):
    return [f for f in sorted(raiz.rglob("*")) if f.is_file() and f.suffix in EXTENSIONES]


# ── AC7: las dos capas existen ──────────────────────────────────────────────

def test_las_dos_capas_existen():
    assert PLATAFORMA.is_dir(), "no hay capa de plataforma"
    assert (PROYECTOS / "alejandria-magazine").is_dir(), "no hay capa de proyecto"
    assert _ficheros(PLATAFORMA) and _ficheros(PROYECTOS)


def test_no_quedan_restos_del_arbol_plano():
    """Si `src/pages/` sigue ahí, la separación es decorativa."""
    for viejo in ("pages", "store", "api", "components", "services", "public"):
        assert not (FUENTE / viejo).exists(), f"src/{viejo}/ sigue existiendo"


# ── La dependencia va en un solo sentido ────────────────────────────────────

def test_la_plataforma_no_importa_de_ningun_proyecto():
    """La guardia de AC7. Un import al revés no rompe nada… hasta el segundo proyecto."""
    culpables = []
    for fichero in _ficheros(PLATAFORMA):
        for numero, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
            for especificador in IMPORT.findall(linea):
                if not especificador.startswith("."):
                    continue
                destino = (fichero.parent / especificador).resolve()
                if PROYECTOS.resolve() in destino.parents:
                    culpables.append(f"{fichero.relative_to(FUENTE)}:{numero} → {especificador}")
    assert culpables == [], (
        "el builder importa de un proyecto concreto: " + str(culpables)
    )


#: Agentes de AlejandrIA cuyo nombre **no** colisiona con nada de la plataforma.
#: `redactor` se queda fuera a propósito: es también un **rol de usuario**, y
#: buscarlo señalaría a `UsersPage`, al menú y al store de flujos, que hablan de
#: permisos y no de agentes.
AGENTES_INEQUIVOCOS = ("investigador", "revisor", "formateador", "publicador")

COMENTARIO = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _sin_comentarios(texto: str) -> str:
    """Los módulos que arreglaron el problema lo explican en sus comentarios."""
    return COMENTARIO.sub("", texto)


def _cuantos_agentes_nombra(fichero: Path) -> int:
    texto = _sin_comentarios(fichero.read_text(encoding="utf-8"))
    return sum(1 for a in AGENTES_INEQUIVOCOS if re.search(rf"['\"]{a}['\"]", texto))


#: Lo que queda del builder mirando a agentes concretos, **con su motivo**. Como
#: en los lints de E7: una excepción escrita es revisable; una tolerancia
#: silenciosa en el umbral del test, no.
RESIDUOS_CONOCIDOS = {
    "platform/components/agents/AgentEditorModal.jsx": (
        "`isFormateador` e `isRedactor` enseñan campos que solo tienen sentido "
        "para esos agentes (formato científico, palabras objetivo). Quitarlos "
        "exige un esquema de campos por agente, que es una tarea aparte."
    ),
}


def test_ningun_fichero_de_la_plataforma_lleva_el_catalogo_de_un_proyecto():
    """`AgentNode`, `AgentsPage` y `FlowDesignerPage` lo tenían escrito dentro."""
    culpables = []
    for fichero in _ficheros(PLATAFORMA):
        cuantos = _cuantos_agentes_nombra(fichero)
        relativa = str(fichero.relative_to(FUENTE))
        if cuantos and relativa not in RESIDUOS_CONOCIDOS:
            culpables.append(f"{relativa} ({cuantos} agentes)")
    assert culpables == [], (
        "el builder nombra agentes de un proyecto concreto: " + str(culpables)
    )


def test_los_residuos_conocidos_siguen_siendo_los_declarados():
    """Si uno se arregla, hay que quitarlo de la lista; si aparece otro, añadirlo."""
    con_agentes = {
        str(f.relative_to(FUENTE))
        for f in _ficheros(PLATAFORMA)
        if _cuantos_agentes_nombra(f) >= 1
    }
    assert con_agentes == set(RESIDUOS_CONOCIDOS), (
        f"la lista de residuos no coincide con la realidad: {con_agentes}"
    )


def test_un_proyecto_si_puede_usar_la_plataforma():
    """El sentido permitido: el consumidor se apoya en el builder."""
    usos = 0
    for fichero in _ficheros(PROYECTOS):
        for especificador in IMPORT.findall(fichero.read_text(encoding="utf-8")):
            if especificador.startswith(".") and (
                PLATAFORMA.resolve() in (fichero.parent / especificador).resolve().parents
            ):
                usos += 1
    assert usos > 0, "ningún proyecto usa la plataforma: la separación sería un muro"


# ── El catálogo de agentes, una sola vez ────────────────────────────────────

def test_el_catalogo_vive_en_el_proyecto():
    assert CATALOGO.is_file()
    contenido = CATALOGO.read_text(encoding="utf-8")
    for agente in ("investigador", "redactor", "revisor", "formateador", "publicador"):
        assert agente in contenido


def test_el_catalogo_no_esta_duplicado():
    """Tres copias es una que se actualiza y dos que no."""
    copias = []
    for fichero in _ficheros(FUENTE):
        if fichero == CATALOGO:
            continue
        texto = fichero.read_text(encoding="utf-8")
        # Una copia del catálogo nombra a varios agentes a la vez.
        nombrados = sum(
            1 for a in ("investigador", "redactor", "revisor", "formateador", "publicador")
            if re.search(rf"^\s*{a}\s*:", texto, re.M)
        )
        if nombrados >= 3:
            copias.append(str(fichero.relative_to(FUENTE)))
    assert copias == [], f"vuelve a haber copias del catálogo de agentes: {copias}"


def test_el_catalogo_se_registra_en_los_dos_puntos_de_arranque():
    """El builder pregunta al pintar el primer nodo: si nadie registró, sale gris."""
    for entrada in (FUENTE / "main.jsx",
                    PROYECTOS / "alejandria-magazine" / "public" / "main.jsx"):
        texto = entrada.read_text(encoding="utf-8")
        assert "setAgentCatalog(" in texto, entrada
        assert "setProjectNavItems(" in texto, entrada


def test_el_menu_del_dashboard_no_trae_articulos_de_serie():
    """«Artículos» es el objeto que produce AlejandrIA, no un concepto del builder."""
    texto = (PLATAFORMA / "pages" / "DashboardPage.jsx").read_text(encoding="utf-8")
    assert "/dashboard/articles" not in texto
    catalogo = CATALOGO.read_text(encoding="utf-8")
    assert "/dashboard/articles" in catalogo


# ── Los dos builds siguen compilando (parte explícita de AC7) ───────────────

def test_las_dos_entradas_de_vite_apuntan_a_ficheros_que_existen():
    """`npm run build` y `build:public` fallan tarde si una entrada se movió."""
    for html, clave in ((FRONT / "index.html", "/src/main.jsx"),
                        (FRONT / "index.public.html", "/src/")):
        contenido = html.read_text(encoding="utf-8")
        encaje = re.search(r'src="(/src/[^"]+)"', contenido)
        assert encaje, f"{html.name} no declara entrada"
        entrada = FRONT / encaje.group(1).lstrip("/")
        assert entrada.is_file(), f"{html.name} apunta a {entrada}, que no existe"
        assert clave in contenido
