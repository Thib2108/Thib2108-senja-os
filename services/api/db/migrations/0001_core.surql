-- 0001_core.surql — verbatim from SDAI-CHAT-003 Block 5 (spec is SSOT)

DEFINE TABLE message SCHEMAFULL;
DEFINE FIELD conversation ON message TYPE record<conversation>;
DEFINE FIELD author  ON message TYPE string ASSERT $value IN ["user", "assistant"];
DEFINE FIELD lane    ON message TYPE string ASSERT $value IN ["message", "cot", "todo", "tool"];
DEFINE FIELD text    ON message TYPE string ASSERT string::len($value) <= 262144; -- 256 KB cap
DEFINE FIELD turn    ON message TYPE int READONLY;              -- server-stamped, monotonic per conversation
DEFINE FIELD created_at ON message TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD embedding  ON message TYPE option<array<float>>;
DEFINE INDEX msg_embedding ON message FIELDS embedding HNSW DIMENSION 768; -- vector index
-- immutability: no UPDATE permission is ever defined for message content

DEFINE TABLE thread SCHEMAFULL;
DEFINE FIELD label ON thread TYPE string;
DEFINE FIELD status ON thread TYPE string ASSERT $value IN ["active", "dormant"];

DEFINE TABLE highlight SCHEMAFULL;
DEFINE FIELD message ON highlight TYPE record<message>;
DEFINE FIELD start ON highlight TYPE int;  DEFINE FIELD end ON highlight TYPE int;
DEFINE FIELD text  ON highlight TYPE string; -- verified at write: text == message.text[start:end]

DEFINE TABLE atom SCHEMAFULL;
DEFINE FIELD thread ON atom TYPE record<thread>;   -- mutable field, NOT part of the id (ADR-04)
DEFINE FIELD label ON atom TYPE string;  DEFINE FIELD body ON atom TYPE string;
DEFINE FIELD status ON atom TYPE string ASSERT $value IN ["new", "updated", "stable", "superseded"];
-- grounding + relations as graph edges:
--   RELATE atom:x -> grounded_by -> highlight:y
--   RELATE atom:a -> relates -> atom:b SET relation="CONVERGES", provenance="inferred", rationale="…"
DEFINE TABLE grounded_by TYPE RELATION FROM atom TO highlight;
DEFINE TABLE relates     TYPE RELATION FROM atom TO atom;
DEFINE FIELD relation   ON relates TYPE string ASSERT $value IN ["CONVERGES", "INTERSECTS", "DEPENDS_ON"];
DEFINE FIELD provenance ON relates TYPE string ASSERT $value IN ["asserted", "inferred"];
DEFINE FIELD rationale  ON relates TYPE option<string>; -- required by service gate when provenance="inferred"

DEFINE TABLE view_block SCHEMAFULL;   -- elements reference atom ids; service gate rejects dangling refs
DEFINE TABLE followup   SCHEMAFULL;
DEFINE TABLE intent_log SCHEMAFULL;   -- the outbox (ADR-03)
DEFINE TABLE decision_log SCHEMAFULL; -- record-once/replay-many cognition log
