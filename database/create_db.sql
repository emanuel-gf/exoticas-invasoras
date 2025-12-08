CREATE EXTENSION postgis;
SELECT pg_reload_conf();
SELECT postgis_full_version();

-- Only run carefully 
DROP TABLE IF EXISTS "manejo";
DROP TABLE IF EXISTS "Manejo1_ps";
DROP TABLE IF EXISTS "ocorrencia";

-- create table manejo
CREATE TABLE "manejo" (
  "id" integer NOT NULL,
  "name" varchar, 
  "elevation" decimal,
  "date" date NOT NULL,
  "time" time NOT NULL,
  "tipo_acao" varchar,
  "zona" integer,
  "especie" varchar NOT NULL,
  "status_remocao" varchar,
  "individuos" integer NOT NULL,
  "plantulas_rev" integer,
  "jovens_rev" integer,
  "adultos_rev" integer,
  "metodo_controle" varchar,
  "mec_controle" varchar,
  "principio_ativo" varchar,
  "quimic_concentr" decimal,
  "quimic_l" decimal,
  "inicio" time,
  "fim" time,
  "num_manej" integer,
  "num_equipe" integer,
  "custo" decimal,
  "geom" geometry NOT NULL,
  "comentario" varchar,
  "description" varchar,
  "created_at" timestamp DEFAULT (CURRENT_TIMESTAMP),
  "updated_at" timestamp DEFAULT (CURRENT_TIMESTAMP),
  PRIMARY KEY ("id")
);


-- create table ocorrencia
CREATE TABLE "ocorrencia" (
  "id" integer NOT NULL,
  "name" varchar(255),
  "elevation" decimal,
  "date" date NOT NULL,
  "time" time NOT NULL,
  "especie" varchar NOT NULL,
  "nivel_prioridade" integer,
  "risco_invasao" integer,
  "estagio_invasao" integer,
  "grau_dispersao" varchar,
  "individuos" integer NOT NULL,
  "zona" integer,
  "estagio_vida" varchar(50),
  "geom" geometry NOT NULL,
  "comentario" varchar(255),
  "description" varchar(255),
  "created_at" timestamp DEFAULT (CURRENT_TIMESTAMP),
  "updated_at" timestamp DEFAULT (CURRENT_TIMESTAMP),
  PRIMARY KEY ("id")
);

-- insert random values to test
INSERT INTO ocorrencia (
    id,  elevation, date, time, especie,
    nivel_prioridade, risco_invasao, estagio_invasao,
    grau_dispersao, individuos, zona, area_degradada,
    geom, comentario, description
    ) VALUES (
        1,
        2.54,
        '2025-12-01',
        '12:30:00',
        'Pinus sp.',
        1,
        2,
        3,
        'A',
        25,
        1,
        'nao',
        ST_SetSRID(ST_Point(-8.12345, 39.12345), 4326),
        'example comment',
        'example description'
    );


INSERT INTO ocorrencia (
    id, elevation, date, time, especie,
    nivel_prioridade, risco_invasao, estagio_invasao,
    grau_dispersao, individuos, zona, area_degradada,
    geom, comentario, description
    )VALUES (
        2,
        3.54,
        '10-12-25',
        '15:30:00',
        'Magnolia sp.',
        2,
        2,
        3,
        'B',
        25,
        1,
        'degradacao por invasao',
        ST_SetSRID(ST_Point(-8.12345, 40.12345), 4326),
        'qlr coisa',
        'exampo le description'
    );

-- select all from table
SELECT * FROM "ocorrencia";
SELECT * FROM "manejo";


-- insert random values
INSERT INTO manejo (
  id, name, elevation, date, time, tipo_acao, zona, especie, status_remocao,
  individuos, plantulas_rev, jovens_rev, adultos_rev,
  metodo_controle, mec_controle, principio_ativo, quimic_concentr, quimic_l,
  inicio, fim, num_manej, num_equipe, custo, geom, comentario, description
    )
    VALUES
    (
    1, 'Área A - Trilha Norte', 120.5, '2025-01-10', '08:30', 'remoção manual', 3, 'Pinus sp.',
    'concluído', 12, 5, 3, 4, 'manual', 'arranquio', NULL, NULL, NULL,
    '08:30', '10:00', 1, 4, 350.00,
    ST_GeomFromText('POINT(-48.1234 -27.5678)', 4326),
    'Remoção sem necessidade de herbicida', 'Manejo de indivíduos jovens de Pinus'
    );

INSERT INTO manejo (
  id, name, elevation, date, time, tipo_acao, zona, especie, status_remocao,
  individuos, plantulas_rev, jovens_rev, adultos_rev,
  metodo_controle, mec_controle, principio_ativo, quimic_concentr, quimic_l,
  inicio, fim, num_manej, num_equipe, custo, geom, comentario, description
    )
    VALUES
    (
    2, 'Área B - Encosta Leste', 305.2, '2025-02-14', '09:15', 'aplicação química', 2, 'Hovenia dulcis',
    'em andamento', 8, 2, 4, 2, 'químico', NULL, 'Glyphosate', 3.5, 1.2,
    '09:15', '11:45', 2, 3, 520.00,
    ST_GeomFromText('POINT(-48.1300 -27.5600)', 4326),
    'Aplicação realizada com bomba costal', 'Controle de indivíduos adultos'
    );

INSERT INTO manejo (
  id, name, elevation, date, time, tipo_acao, zona, especie, status_remocao,
  individuos, plantulas_rev, jovens_rev, adultos_rev,
  metodo_controle, mec_controle, principio_ativo, quimic_concentr, quimic_l,
  inicio, fim, num_manej, num_equipe, custo, geom, comentario, description
    )
    VALUES
    (
    3, 'Área C - Vale Central', 98.7, '2025-03-02', '07:50', 'monitoramento', 1, 'Tradescantia zebrina',
    'não removido', 0, 15, 0, 0, NULL, NULL, NULL, NULL, NULL,
    '07:50', '09:00', 1, 2, 180.00,
    ST_GeomFromText('POINT(-48.1100 -27.5700)', 4326),
    'Apenas monitoramento, sem ação de controle', 'Registro de densidade de cobertura'
    );


-- query the col, datatype an nullable on the table manejo
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'manejo' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- query spatial index
SELECT f_geometry_column, coord_dimension, srid, type
FROM geometry_columns
WHERE f_table_name = 'ocorrencia';


SELECT * FROM "manejo";