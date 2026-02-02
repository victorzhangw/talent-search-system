-- 03_add_trait_project.sql
-- Add trait_project column to trait_bands table and populate it with the first 3 characters of trait_id

-- 1. Add the column
ALTER TABLE trait_bands 
ADD COLUMN IF NOT EXISTS trait_project VARCHAR(50),
ADD COLUMN IF NOT EXISTS report_wording_friendly TEXT;

-- 2. Populate the column with the first 3 characters of trait_id
UPDATE trait_bands 
SET trait_project = SUBSTRING(trait_id, 1, 3);

-- 3. Add Unique Constraints for Upsert support (ON CONFLICT)
ALTER TABLE trait_bands 
ADD CONSTRAINT uq_trait_bands UNIQUE (trait_id, band);

ALTER TABLE trait_interactions 
ADD CONSTRAINT uq_trait_interactions UNIQUE (primary_trait_id, primary_band, trigger_trait_id, trigger_band);

