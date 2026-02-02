-- 04_add_v4_extras.sql
-- Add V4 specific extra columns to trait_bands

ALTER TABLE trait_bands
ADD COLUMN IF NOT EXISTS usage_note TEXT,
ADD COLUMN IF NOT EXISTS hidden_anchor TEXT,
ADD COLUMN IF NOT EXISTS trait_interaction_guide TEXT;
