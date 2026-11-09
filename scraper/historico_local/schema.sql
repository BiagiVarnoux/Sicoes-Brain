PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
 run_id TEXT PRIMARY KEY, mode TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
 parameters_json TEXT NOT NULL, code_json TEXT NOT NULL, status TEXT NOT NULL,
 discovery_status TEXT NOT NULL DEFAULT 'not_started', error_json TEXT);
CREATE TABLE IF NOT EXISTS processes (
 cuce TEXT PRIMARY KEY, entity TEXT NOT NULL, year INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS discoveries (
 run_id TEXT NOT NULL REFERENCES runs, cuce TEXT NOT NULL REFERENCES processes,
 metadata_json TEXT NOT NULL, PRIMARY KEY(run_id,cuce));
CREATE TABLE IF NOT EXISTS discovery_pages (
 run_id TEXT NOT NULL REFERENCES runs, page INTEGER NOT NULL, sha256 TEXT NOT NULL,
 path TEXT NOT NULL, cuces_json TEXT NOT NULL, links_json TEXT NOT NULL,
 PRIMARY KEY(run_id,page));
CREATE TABLE IF NOT EXISTS documents (
 document_id TEXT PRIMARY KEY, cuce TEXT NOT NULL REFERENCES processes, kind TEXT NOT NULL,
 label TEXT NOT NULL, occurrence INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS document_inventory (
 run_id TEXT NOT NULL REFERENCES runs, document_id TEXT NOT NULL REFERENCES documents,
 availability TEXT NOT NULL, metadata_json TEXT NOT NULL, PRIMARY KEY(run_id,document_id));
CREATE TABLE IF NOT EXISTS artifacts (
 sha256 TEXT PRIMARY KEY, path TEXT NOT NULL, bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS document_versions (
 version_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents,
 raw_sha256 TEXT NOT NULL REFERENCES artifacts, detected_type TEXT NOT NULL,
 validation_status TEXT NOT NULL, validation_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempts (
 attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs, document_id TEXT NOT NULL REFERENCES documents,
 started_at TEXT NOT NULL, finished_at TEXT, outcome TEXT NOT NULL, version_id TEXT REFERENCES document_versions,
 capture_status TEXT NOT NULL, conversion_status TEXT NOT NULL, parse_status TEXT NOT NULL,
 errors_json TEXT NOT NULL, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS parses (
 parse_id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES document_versions,
 parser_version TEXT NOT NULL, status TEXT NOT NULL, raw_rows INTEGER NOT NULL,
 item_rows INTEGER NOT NULL, generic_rows INTEGER NOT NULL, warnings_json TEXT NOT NULL,
 structured_sha256 TEXT NOT NULL REFERENCES artifacts, markdown_sha256 TEXT REFERENCES artifacts);
CREATE TABLE IF NOT EXISTS observations (
 observation_id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES document_versions,
 section TEXT NOT NULL, table_position INTEGER NOT NULL, row_position INTEGER NOT NULL,
 row_kind TEXT NOT NULL, raw_cells_json TEXT NOT NULL, raw_html TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS normalizations (
 parse_id TEXT NOT NULL REFERENCES parses, observation_id TEXT NOT NULL REFERENCES observations,
 fields_json TEXT NOT NULL, PRIMARY KEY(parse_id,observation_id));
CREATE INDEX IF NOT EXISTS idx_docs_cuce ON documents(cuce);
CREATE INDEX IF NOT EXISTS idx_observations_version ON observations(version_id);
-- No identidad ni colapso entre fases. Vista de todos los parseos, nunca reemplazo destructivo.
CREATE VIEW IF NOT EXISTS parsed_documents AS
 SELECT d.cuce,d.document_id,d.kind,v.version_id,p.parse_id,p.status,p.raw_rows,p.item_rows
 FROM documents d JOIN document_versions v USING(document_id) JOIN parses p USING(version_id);
