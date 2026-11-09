PRAGMA foreign_keys=ON;
CREATE TABLE documentos (
 document_id TEXT PRIMARY KEY, cuce TEXT NOT NULL, formulario TEXT NOT NULL,
 ruta_origen TEXT NOT NULL, sha256_origen TEXT NOT NULL, manifest_key TEXT NOT NULL,
 estado TEXT NOT NULL, motivo_exclusion TEXT, contexto_json TEXT NOT NULL, alertas_json TEXT NOT NULL);
CREATE TABLE tablas (
 document_id TEXT NOT NULL REFERENCES documentos, tabla INTEGER NOT NULL,
 seccion TEXT NOT NULL, clasificacion TEXT NOT NULL, auditoria_json TEXT NOT NULL,
 PRIMARY KEY(document_id,tabla));
CREATE TABLE filas_originales (
 document_id TEXT NOT NULL REFERENCES documentos, tabla INTEGER NOT NULL, fila INTEGER NOT NULL,
 clasificacion TEXT NOT NULL, celdas_json TEXT NOT NULL, html_fila TEXT,
 PRIMARY KEY(document_id,tabla,fila), FOREIGN KEY(document_id,tabla) REFERENCES tablas);
CREATE TABLE observaciones (
 observation_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documentos,
 cuce TEXT NOT NULL, formulario TEXT NOT NULL, etapa TEXT NOT NULL, estado_evento TEXT NOT NULL,
 seccion TEXT NOT NULL, seccion_id TEXT NOT NULL, tabla INTEGER NOT NULL, fila INTEGER NOT NULL,
 descripcion_original TEXT NOT NULL, descripcion_visible TEXT NOT NULL, rol_demanda TEXT NOT NULL,
 alertas_json TEXT NOT NULL, FOREIGN KEY(document_id,tabla,fila) REFERENCES filas_originales);
CREATE TABLE atributos_originales (
 observation_id TEXT NOT NULL REFERENCES observaciones, columna INTEGER NOT NULL,
 encabezado_original TEXT NOT NULL, atributo TEXT NOT NULL, valor_original TEXT NOT NULL,
 valor_visible TEXT NOT NULL, valor_normalizado TEXT, estado_normalizacion TEXT NOT NULL,
 normalizacion_json TEXT NOT NULL, PRIMARY KEY(observation_id,columna));
CREATE TABLE atributos_derivados (
 observation_id TEXT NOT NULL REFERENCES observaciones, atributo TEXT NOT NULL, valor TEXT NOT NULL,
 formula TEXT NOT NULL, evidencia_calculo_json TEXT NOT NULL, PRIMARY KEY(observation_id,atributo));
CREATE TABLE contextos_contrato (
 document_id TEXT NOT NULL REFERENCES documentos, tabla INTEGER NOT NULL, fila INTEGER NOT NULL,
 campos_json TEXT NOT NULL, PRIMARY KEY(document_id,tabla,fila));
CREATE TABLE metadatos (clave TEXT PRIMARY KEY, valor_json TEXT NOT NULL);
CREATE INDEX idx_obs_fase ON observaciones(cuce,formulario,etapa);
CREATE VIEW resumen_observaciones AS
 SELECT o.*,d.ruta_origen,d.sha256_origen FROM observaciones o JOIN documentos d USING(document_id);
