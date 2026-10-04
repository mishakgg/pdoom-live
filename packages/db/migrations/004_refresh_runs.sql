-- Refresh runs record unchanged, skipped, and failed counts beside new and changed.
-- A partial run is not a full success. Existing succeeded and failed rows stay valid.

ALTER TABLE ingestion_runs ADD COLUMN unchanged_count integer NOT NULL DEFAULT 0 CHECK (unchanged_count >= 0);
ALTER TABLE ingestion_runs ADD COLUMN skipped_count integer NOT NULL DEFAULT 0 CHECK (skipped_count >= 0);
ALTER TABLE ingestion_runs ADD COLUMN failed_count integer NOT NULL DEFAULT 0 CHECK (failed_count >= 0);

ALTER TABLE ingestion_runs DROP CONSTRAINT ingestion_runs_status_check;
ALTER TABLE ingestion_runs ADD CONSTRAINT ingestion_runs_status_check
  CHECK (status IN ('running', 'succeeded', 'partial', 'failed'));
