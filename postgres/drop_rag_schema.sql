-- Drop view
DROP VIEW IF EXISTS content_units_with_images CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS get_image_for_unit(UUID);
DROP FUNCTION IF EXISTS get_pdf_section(UUID);

-- Drop tables (CASCADE removes indexes + FKs)
DROP TABLE IF EXISTS content_units CASCADE;
DROP TABLE IF EXISTS image_assets CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
