<?php
/**
 * Plantilla de configuración. COPIAR a `db.php` EN EL SERVIDOR y rellenar.
 *
 * `db.php` contiene secretos y NO se versiona (está en .gitignore).
 * Súbelo solo a Hostinger (public_html/api/db.php), nunca al repo.
 *
 * En hosting compartido de Hostinger el host de MySQL suele ser "localhost".
 */

return [
    // ── MySQL (hPanel → Bases de datos MySQL) ──────────────────────────────
    'db_host' => 'localhost',
    'db_name' => 'uXXXXXXXXX_revista',     // nombre de la BD creada en hPanel
    'db_user' => 'uXXXXXXXXX_revista',     // usuario MySQL
    'db_pass' => 'CAMBIA_ESTA_PASSWORD',   // contraseña del usuario MySQL

    // ── Token de ingesta ───────────────────────────────────────────────────
    // El mismo valor debe ir en la variable de entorno HOSTINGER_INGEST_TOKEN
    // del script local scripts/publish_to_hostinger.py.
    // Genera uno con: openssl rand -hex 32
    'ingest_token' => 'CAMBIA_ESTE_TOKEN',
];
