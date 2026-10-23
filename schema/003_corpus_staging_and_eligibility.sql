ALTER TABLE source_text_versions ADD COLUMN registry_id TEXT UNIQUE;
ALTER TABLE source_text_versions ADD COLUMN rights_status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE source_text_versions ADD COLUMN editorial_status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE source_text_versions ADD COLUMN provenance JSONB NOT NULL DEFAULT '{}';
ALTER TABLE translations ADD COLUMN registry_id TEXT UNIQUE;
ALTER TABLE translations ADD COLUMN provider_release_date TEXT;
ALTER TABLE translations ADD COLUMN historical_publication_date TEXT;
ALTER TABLE translations ADD COLUMN preparation_status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE translations ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE aligned_segments ADD COLUMN paper_facing_eligible BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE aligned_segments ADD COLUMN review_status TEXT NOT NULL DEFAULT 'unreviewed';
ALTER TABLE aligned_segments ADD COLUMN analysis_status TEXT NOT NULL DEFAULT 'excluded';
ALTER TABLE analysis_runs ADD COLUMN run_key TEXT UNIQUE;
ALTER TABLE analysis_runs ADD COLUMN source_revision TEXT;
ALTER TABLE analysis_runs ADD COLUMN analysis_mode TEXT NOT NULL DEFAULT 'legacy_bootstrap';
ALTER TABLE site_builds ADD COLUMN source_revision TEXT;
ALTER TABLE site_builds ADD COLUMN finished_at TIMESTAMPTZ;

-- Prepared text and review state are deliberately separate from aligned_segments.
CREATE TABLE corpus_artifacts (
    kind TEXT NOT NULL CHECK (kind IN ('source_line', 'translation_book',
        'book_alignment', 'candidate', 'review', 'reviewed_alignment')),
    registry_id TEXT NOT NULL,
    work_id BIGINT NOT NULL REFERENCES works(id),
    source_version_id BIGINT REFERENCES source_text_versions(id),
    translation_id BIGINT REFERENCES translations(id),
    book INTEGER NOT NULL CHECK (book > 0),
    status TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    payload JSONB NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (kind, registry_id)
);
CREATE INDEX corpus_artifacts_inventory_idx ON corpus_artifacts(work_id, kind) WHERE is_current;
CREATE TABLE corpus_sync_state (
    singleton BOOLEAN PRIMARY KEY DEFAULT true CHECK (singleton),
    manifest_hash TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE alignment_adjudications (
    candidate_id TEXT PRIMARY KEY,
    reviewed_sha256 TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject')),
    adjudicator TEXT NOT NULL CHECK (btrim(adjudicator) <> ''),
    adjudicated_at TIMESTAMPTZ NOT NULL,
    notes TEXT NOT NULL,
    aligned_segment_id BIGINT UNIQUE REFERENCES aligned_segments(id)
);

CREATE VIEW paper_facing_segments AS
SELECT s.* FROM aligned_segments s
JOIN translations t ON t.id=s.translation_id AND t.work_id=s.work_id
JOIN source_text_versions v ON v.id=s.source_version_id AND v.work_id=s.work_id
WHERE s.paper_facing_eligible AND s.review_status='adjudicated'
  AND s.analysis_status='eligible'
  AND s.alignment_level='reviewed_source_line_range_to_translation_paragraph'
  AND NOT t.is_machine_generated AND t.translation_source_type='existing_human_translation'
  AND t.license_status IN ('public_domain_us','public_domain_worldwide','open_license')
  AND v.rights_status IN ('public_domain_us','public_domain_worldwide','open_license')
  AND v.editorial_status='human_edited_published'
  AND v.provenance->>'paper_facing_eligible'='yes'
  AND t.metadata->>'paper_facing_eligible'='yes'
  AND EXISTS (SELECT 1 FROM alignment_adjudications a
      JOIN corpus_artifacts r ON r.kind='reviewed_alignment'
          AND r.registry_id=a.candidate_id AND r.is_current AND r.sha256=a.reviewed_sha256
      WHERE a.aligned_segment_id=s.id AND a.decision='approve'
        AND r.source_version_id=s.source_version_id AND r.translation_id=s.translation_id
        AND r.payload->>'source_prepared_sha256'=v.text_hash
        AND r.payload->>'translation_prepared_sha256'=t.text_hash
        AND r.payload->>'source_text'=s.source_text AND r.payload->>'target_text'=s.target_text);

CREATE VIEW corpus_preparation_inventory AS
SELECT w.slug,
  (SELECT count(*) FROM translations t WHERE t.work_id=w.id AND t.registry_id IS NOT NULL) AS published_translations,
  count(*) FILTER (WHERE a.kind='source_line') AS source_lines,
  count(*) FILTER (WHERE a.kind='translation_book') AS translation_books,
  count(*) FILTER (WHERE a.kind='book_alignment') AS book_pairs,
  count(*) FILTER (WHERE a.kind='candidate') AS candidates,
  count(*) FILTER (WHERE a.kind='review' AND coalesce(a.payload->>'review_decision','')<>'') AS entered_reviews,
  count(*) FILTER (WHERE a.kind='reviewed_alignment') AS validated_reviews,
  (SELECT count(*) FROM paper_facing_segments s WHERE s.work_id=w.id) AS paper_facing_segments
FROM works w LEFT JOIN corpus_artifacts a ON a.work_id=w.id AND a.is_current
GROUP BY w.id, w.slug;
