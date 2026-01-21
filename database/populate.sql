--- 
--- POPULATING THE "ocorrencia" TABLE (10 Samples)
---

INSERT INTO "ocorrencia" (id, name, elevation, date, time, especie, nivel_prioridade, risco_invasao, estagio_invasao, grau_dispersao, individuos, zona, geom, comentario, description)
VALUES 
(1, 'Ponto 01', 2.54, '2025-12-01', '12:30:00', 'Pinus sp.', 1, 2, 3, 'A', 25, 1, ST_SetSRID(ST_Point(-48.1234, -27.5678), 4326), 'Comentário exemplo 1', 'Descrição exemplo 1'),
(2, 'Ponto 02', 3.54, '2025-12-10', '15:30:00', 'Magnolia sp.', 2, 2, 3, 'B', 15, 1, ST_SetSRID(ST_Point(-48.1245, -27.5689), 4326), 'Comentário exemplo 2', 'Descrição exemplo 2'),
(3, 'Ponto 03', 15.20, '2026-01-05', '09:00:00', 'Hovenia dulcis', 3, 3, 4, 'C', 50, 2, ST_SetSRID(ST_Point(-48.1300, -27.5600), 4326), 'Foco denso', 'Área de encosta'),
(4, 'Ponto 04', 122.0, '2026-01-08', '10:15:00', 'Hedychium coronarium', 1, 1, 2, 'A', 10, 3, ST_SetSRID(ST_Point(-48.1100, -27.5700), 4326), 'Beira de riacho', 'Perto da zona de preservação'),
(5, 'Ponto 05', 45.00, '2026-01-12', '14:20:00', 'Pinus sp.', 2, 2, 2, 'B', 8, 1, ST_SetSRID(ST_Point(-48.1150, -27.5750), 4326), 'Indivíduos jovens', 'Expansão norte'),
(6, 'Ponto 06', 88.50, '2026-01-15', '08:45:00', 'Tradescantia zebrina', 3, 1, 5, 'D', 100, 2, ST_SetSRID(ST_Point(-48.1400, -27.5800), 4326), 'Cobertura total', 'Sub-bosque degradado'),
(7, 'Ponto 07', 10.10, '2026-01-18', '11:00:00', 'Psidium guajava', 1, 1, 1, 'A', 2, 4, ST_SetSRID(ST_Point(-48.1200, -27.5500), 4326), 'Início de dispersão', 'Próximo à trilha principal'),
(8, 'Ponto 08', 210.0, '2026-01-20', '16:30:00', 'Pinus sp.', 3, 3, 4, 'C', 40, 3, ST_SetSRID(ST_Point(-48.1500, -27.5900), 4326), 'Necessita intervenção urgente', 'Topo de morro'),
(9, 'Ponto 09', 5.00, '2026-01-21', '07:30:00', 'Urochloa maxima', 2, 3, 3, 'B', 60, 1, ST_SetSRID(ST_Point(-48.1000, -27.5400), 4326), 'Gramínea invasora', 'Área aberta'),
(10, 'Ponto 10', 32.40, '2026-01-21', '13:00:00', 'Melinis repens', 1, 2, 2, 'A', 20, 2, ST_SetSRID(ST_Point(-48.1050, -27.5350), 4326), 'Beira de estrada', 'Vetor de dispersão');

--- 
--- POPULATING THE "manejo" TABLE (10 Samples)
---

INSERT INTO "manejo" (id, name, elevation, date, time, tipo_acao, zona, especie, status_remocao, individuos, plantulas_rev, jovens_rev, adultos_rev, metodo_controle, mec_controle, principio_ativo, quimic_concentr, quimic_l, inicio, fim, num_manej, num_equipe, custo, geom, comentario, description)
VALUES 
(1, 'Manejo A', 120.5, '2025-01-10', '08:30:00', 'remoção manual', 3, 'Pinus sp.', 'concluído', 12, 5, 3, 4, 'manual', 'arranquio', NULL, NULL, NULL, '08:30:00', '10:00:00', 1, 4, 350.00, ST_GeomFromText('POINT(-48.1234 -27.5678)', 4326), 'Sem herbicida', 'Manejo de jovens'),
(2, 'Manejo B', 305.2, '2025-02-14', '09:15:00', 'aplicação química', 2, 'Hovenia dulcis', 'em andamento', 8, 2, 4, 2, 'químico', NULL, 'Glyphosate', 3.5, 1.2, '09:15:00', '11:45:00', 2, 3, 520.00, ST_GeomFromText('POINT(-48.1300 -27.5600)', 4326), 'Bomba costal', 'Controle adultos'),
(3, 'Manejo C', 98.7, '2025-03-02', '07:50:00', 'monitoramento', 1, 'Tradescantia zebrina', 'não removido', 0, 15, 0, 0, NULL, NULL, NULL, NULL, NULL, '07:50:00', '09:00:00', 1, 2, 180.00, ST_GeomFromText('POINT(-48.1100 -27.5700)', 4326), 'Apenas registro', 'Densidade alta'),
(4, 'Manejo D', 45.0, '2025-03-15', '08:00:00', 'remoção mecânica', 1, 'Pinus sp.', 'concluído', 20, 10, 5, 5, 'mecânico', 'roçadeira', NULL, NULL, NULL, '08:00:00', '12:00:00', 3, 5, 750.00, ST_GeomFromText('POINT(-48.1150 -27.5750)', 4326), 'Uso de motosserra para adultos', 'Limpeza de borda'),
(5, 'Manejo E', 15.0, '2025-04-10', '13:30:00', 'aplicação química', 4, 'Psidium guajava', 'concluído', 5, 0, 2, 3, 'químico', 'anelamento', 'Triclopyr', 2.0, 0.5, '13:30:00', '15:30:00', 1, 2, 420.00, ST_GeomFromText('POINT(-48.1200 -27.5500)', 4326), 'Anelamento com pincelamento', 'Área de difícil acesso'),
(6, 'Manejo F', 10.5, '2025-05-05', '09:00:00', 'remoção manual', 1, 'Hedychium coronarium', 'concluído', 30, 20, 10, 0, 'manual', 'arranquio manual', NULL, NULL, NULL, '09:00:00', '11:00:00', 4, 6, 200.00, ST_GeomFromText('POINT(-48.1000 -27.5400)', 4326), 'Retirada de rizomas', 'Área úmida'),
(7, 'Manejo G', 210.0, '2025-06-20', '08:00:00', 'remoção mecânica', 3, 'Pinus sp.', 'parcial', 15, 0, 0, 15, 'mecânico', 'corte raso', NULL, NULL, NULL, '08:00:00', '17:00:00', 5, 8, 1200.00, ST_GeomFromText('POINT(-48.1500 -27.5900)', 4326), 'Equipe grande necessária', 'Declividade alta'),
(8, 'Manejo H', 32.0, '2025-07-12', '10:00:00', 'monitoramento', 2, 'Melinis repens', 'não removido', 0, 0, 0, 0, NULL, NULL, NULL, NULL, NULL, '10:00:00', '11:00:00', 1, 2, 100.00, ST_GeomFromText('POINT(-48.1050 -27.5350)', 4326), 'Vistoria pós-fogo', 'Recuperação natural'),
(9, 'Manejo I', 88.0, '2025-08-05', '08:30:00', 'remoção manual', 2, 'Tradescantia zebrina', 'em andamento', 50, 50, 0, 0, 'manual', 'rastelagem', NULL, NULL, NULL, '08:30:00', '12:00:00', 2, 4, 300.00, ST_GeomFromText('POINT(-48.1400 -27.5800)', 4326), 'Mão de obra voluntária', 'Projeto Restauro'),
(10, 'Manejo J', 5.5, '2025-09-01', '14:00:00', 'aplicação química', 1, 'Urochloa maxima', 'concluído', 10, 0, 0, 10, 'químico', 'pulverização', 'Glyphosate', 4.0, 2.5, '14:00:00', '16:30:00', 3, 3, 480.00, ST_GeomFromText('POINT(-48.1000 -27.5400)', 4326), 'Controle de gramínea', 'Preparação para plantio');