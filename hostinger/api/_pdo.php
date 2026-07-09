<?php
/**
 * Helper compartido: abre una conexión PDO a MySQL usando db.php.
 * Devuelve [PDO $pdo, array $cfg].
 */
function open_db(): array
{
    $cfgPath = __DIR__ . '/db.php';
    if (!is_file($cfgPath)) {
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['error' => 'Falta db.php en el servidor']);
        exit;
    }
    $cfg = require $cfgPath;

    $dsn = sprintf(
        'mysql:host=%s;dbname=%s;charset=utf8mb4',
        $cfg['db_host'],
        $cfg['db_name']
    );
    try {
        $pdo = new PDO($dsn, $cfg['db_user'], $cfg['db_pass'], [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
    } catch (Throwable $e) {
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['error' => 'No se pudo conectar a la base de datos']);
        exit;
    }

    return [$pdo, $cfg];
}
