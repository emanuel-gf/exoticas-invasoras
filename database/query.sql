
-- select all from table
SELECT * FROM "ocorrencia";
SELECT * FROM "manejo";



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