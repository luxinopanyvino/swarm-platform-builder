<?php
/**
 * Endpoint de ingesta (escritura) — protegido por token.
 *
 * Recibe del script local (scripts/publish_to_hostinger.py) los artículos
 * publicados y los inserta/actualiza en MySQL (upsert por id).
 *
 * Auth: header `X-Ingest-Token` debe coincidir con cfg['ingest_token'].
 * Body: JSON. Acepta un objeto artículo o una lista de artículos.
 */
require __DIR__ . '/_pdo.php';

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

[$pdo, $cfg] = open_db();

// ── Auth por token (comparación en tiempo constante) ───────────────────────
$token = $_SERVER['HTTP_X_INGEST_TOKEN'] ?? '';
if (!is_string($token) || !hash_equals((string)$cfg['ingest_token'], $token)) {
    http_response_code(401);
    echo json_encode(['error' => 'Token inválido']);
    exit;
}

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data)) {
    http_response_code(400);
    echo json_encode(['error' => 'JSON inválido']);
    exit;
}

// Permitir un solo artículo o una lista.
$articles = array_is_list($data) ? $data : [$data];

$sql = 'INSERT INTO articles (id, title, body, abstract, authors, cover_url, published_at, updated_at)
        VALUES (:id, :title, :body, :abstract, :authors, :cover_url, :published_at, :updated_at)
        ON DUPLICATE KEY UPDATE
            title=VALUES(title), body=VALUES(body), abstract=VALUES(abstract),
            authors=VALUES(authors), cover_url=VALUES(cover_url),
            published_at=VALUES(published_at), updated_at=VALUES(updated_at)';
$stmt = $pdo->prepare($sql);

$count = 0;
$pdo->beginTransaction();
try {
    foreach ($articles as $a) {
        if (empty($a['id']) || empty($a['title'])) {
            continue; // saltar registros sin campos obligatorios
        }
        $stmt->execute([
            ':id'           => (string)$a['id'],
            ':title'        => (string)$a['title'],
            ':body'         => (string)($a['body'] ?? ''),
            ':abstract'     => $a['abstract'] ?? null,
            ':authors'      => json_encode($a['authors'] ?? [], JSON_UNESCAPED_UNICODE),
            ':cover_url'    => $a['cover_url'] ?? null,
            ':published_at' => $a['published_at'] ?? null,
            ':updated_at'   => $a['updated_at'] ?? null,
        ]);
        $count++;
    }
    $pdo->commit();
} catch (Throwable $e) {
    $pdo->rollBack();
    http_response_code(500);
    echo json_encode(['error' => 'Error al guardar']);
    exit;
}

echo json_encode(['ok' => true, 'upserted' => $count]);
