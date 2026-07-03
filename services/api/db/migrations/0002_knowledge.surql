-- 0002_knowledge.surql — per SDAI-CHAT-004 Block 5 migration sketch

DEFINE TABLE knowledge_item SCHEMAFULL;   -- envelope fields + lifecycle + sensitivity
DEFINE TABLE facet_assignment SCHEMAFULL; -- (item, facet, value, tag_source, confidence)
DEFINE TABLE trust_event SCHEMAFULL;      -- append-only, no UPDATE permission
-- relation tables generated from the Edge Registry (derived_from, published_by,
-- superseded_by, grounded_by, corroborates, contradicts, part_of, depends_on, ...)
DEFINE INDEX item_hash ON knowledge_item FIELDS content_hash UNIQUE; -- dedupe no-op
