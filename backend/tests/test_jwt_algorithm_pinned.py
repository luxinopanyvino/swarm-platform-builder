"""Sostiene las excepciones de pip-audit de python-jose (PYSEC-2026-1325 y PYSEC-2026-4298).

Ambas se ignoran en `.github/workflows/ci.yml` porque no son explotables **mientras**:

* el algoritmo sea HMAC (HS256…), con una clave simétrica y no una pública/privada, y
* `jwt.decode` restrinja siempre `algorithms` a ese valor.

Si alguna cambia, la excepción deja de estar justificada y este test falla para
obligar a quitarla (o a revisar el cambio) en vez de heredarla en silencio.
"""
import re
from pathlib import Path

from app.core.config import settings

SEGURIDAD = Path(__file__).resolve().parents[1] / "app" / "core" / "security.py"
CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def test_el_algoritmo_es_hmac():
    assert settings.ALGORITHM.upper().startswith("HS"), (
        "El algoritmo ya no es HMAC: quita --ignore-vuln PYSEC-2026-1325 y PYSEC-2026-4298 de la CI "
        "antes de seguir (la confusión de algoritmos de python-jose pasa a ser explotable)."
    )


def test_cada_decode_restringe_los_algoritmos():
    fuente = SEGURIDAD.read_text(encoding="utf-8")
    decodes = re.findall(r"jwt\.decode\((.*?)\)\s*$", fuente, re.MULTILINE)
    assert decodes, "no se encontró ningún jwt.decode: ¿se movió la verificación?"
    for llamada in decodes:
        assert "algorithms=[settings.ALGORITHM]" in llamada, f"jwt.decode sin restringir algoritmos: {llamada}"


def test_no_hay_otros_usos_de_jose_en_la_aplicacion():
    app = Path(__file__).resolve().parents[1] / "app"
    usos = [
        str(p.relative_to(app)) for p in app.rglob("*.py")
        if "from jose" in p.read_text(encoding="utf-8") or "import jose" in p.read_text(encoding="utf-8")
    ]
    assert [u.replace("\\", "/") for u in usos] == ["core/security.py"]


def test_la_ci_documenta_las_dos_excepciones():
    ci = CI.read_text(encoding="utf-8")
    for vuln in ("PYSEC-2026-1325", "PYSEC-2026-4298"):
        assert f"--ignore-vuln {vuln}" in ci
