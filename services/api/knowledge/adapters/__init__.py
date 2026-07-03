"""Per-category adapters — file type changes the adapter, NEVER the spine (004 Principle 1).

Categories: prose · slides · image_ocr · audio_transcript · code.
Docling is an optional dependency group; absence degrades to the plain-text
adapter and is logged at startup — never crashes the spine.

A file-type `if` below the waist is a defect (test_no_filetype_branch_below_the_waist).
"""

ADAPTERS: dict[str, object] = {}  # TODO(004-slice): register adapters by detected category
