-- Esquema MySQL para la revista pública en Hostinger (hosting compartido).
-- Solo el subconjunto público de los artículos PUBLICADOS.
-- Ejecutar una vez en phpMyAdmin (hPanel → Bases de datos → phpMyAdmin).

CREATE TABLE IF NOT EXISTS articles (
  id           VARCHAR(36)  NOT NULL,          -- UUID del artículo en la plataforma local
  title        VARCHAR(512) NOT NULL,
  body         LONGTEXT     NOT NULL,          -- cuerpo en markdown
  abstract     TEXT         NULL,
  authors      JSON         NULL,              -- lista de autores
  cover_url    VARCHAR(1024) NULL,
  published_at DATETIME     NULL,
  updated_at   DATETIME     NULL,
  PRIMARY KEY (id),
  KEY idx_published (published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
