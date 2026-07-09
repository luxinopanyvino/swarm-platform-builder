<?php
/**
 * Endpoint público de la revista (reemplaza a GET /api/v1/magazine de FastAPI).
 *
 * Devuelve los artículos publicados como JSON, con la misma forma que espera
 * el frontend (frontend/src/pages/MagazinePage.jsx).
 *
 * El .htaccess reescribe /api/v1/magazine -> este archivo, así el frontend no
 * necesita cambios.
 */
require __DIR__ . '/_pdo.php';

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

[$pdo, $cfg] = open_db();

$skip  = max(0, (int)($_GET['skip'] ?? 0));
$limit = min(100, max(1, (int)($_GET['limit'] ?? 50)));

$stmt = $pdo->prepare(
    'SELECT id, title, body, abstract, authors, cover_url, published_at, updated_at
       FROM articles
      WHERE published_at IS NOT NULL
      ORDER BY published_at DESC
      LIMIT :limit OFFSET :skip'
);
$stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
$stmt->bindValue(':skip', $skip, PDO::PARAM_INT);
$stmt->execute();

$rows = array_map(static function (array $r): array {
    $r['authors'] = $r['authors'] !== null ? json_decode($r['authors'], true) : [];
    if (!is_array($r['authors'])) {
        $r['authors'] = [];
    }
    return $r;
}, $stmt->fetchAll());

echo json_encode($rows, JSON_UNESCAPED_UNICODE);
