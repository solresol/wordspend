ALTER TABLE works
    ADD COLUMN IF NOT EXISTS planned_target_languages TEXT;

ALTER TABLE works
    ADD COLUMN IF NOT EXISTS translation_plan TEXT;

ALTER TABLE translations
    ADD COLUMN IF NOT EXISTS publication_date TEXT;

ALTER TABLE translations
    ADD COLUMN IF NOT EXISTS edition_citation TEXT;

ALTER TABLE translations
    ADD COLUMN IF NOT EXISTS download_url TEXT;

ALTER TABLE translations
    ADD COLUMN IF NOT EXISTS rights_statement TEXT;

ALTER TABLE translations
    ADD COLUMN IF NOT EXISTS translation_source_type TEXT NOT NULL DEFAULT 'existing_human_translation';

ALTER TABLE translations
    ADD COLUMN IF NOT EXISTS is_machine_generated BOOLEAN NOT NULL DEFAULT false;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'works'
          AND column_name = 'target_language'
    ) THEN
        EXECUTE 'UPDATE works SET planned_target_languages = target_language WHERE planned_target_languages IS NULL';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'works'
          AND column_name = 'translation_provenance'
    ) THEN
        EXECUTE 'UPDATE works SET translation_plan = translation_provenance WHERE translation_plan IS NULL';
    END IF;
END
$$;

DROP VIEW IF EXISTS corpus_inventory;

CREATE VIEW corpus_inventory AS
SELECT
    w.slug,
    w.title,
    w.author,
    w.source_language,
    coalesce(
        nullif(string_agg(DISTINCT t.target_language, '; ' ORDER BY t.target_language), ''),
        w.planned_target_languages
    ) AS target_languages,
    w.genre,
    w.priority,
    w.status,
    count(s.id)::integer AS segment_count,
    coalesce(sum(s.source_token_count), 0)::integer AS source_tokens,
    coalesce(sum(s.target_token_count), 0)::integer AS target_tokens
FROM works w
LEFT JOIN aligned_segments s ON s.work_id = w.id
LEFT JOIN translations t ON t.id = s.translation_id
GROUP BY
    w.slug,
    w.title,
    w.author,
    w.source_language,
    w.planned_target_languages,
    w.genre,
    w.priority,
    w.status
ORDER BY
    CASE w.priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        ELSE 3
    END,
    w.source_language,
    w.title;
