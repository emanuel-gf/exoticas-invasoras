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

