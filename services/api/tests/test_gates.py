"""Gate unit tests — the load-bearing invariant gets the first real coverage.

verify_verbatim comes from the shared kernel (004 ADR-04): one gate, imported
everywhere, tested here once.
"""

from gatesvc import check_inferred_edge, check_view_block_refs
from harness_kernel.gates import verify_verbatim

SOURCE = "The fa\u00e7ade package 🏗️ moves to #stage/build next week."


def test_verbatim_accepts_exact_slice():
    quote = SOURCE[4:19]
    assert verify_verbatim(quote, SOURCE, 4, 19)


def test_verbatim_rejects_off_by_one():
    quote = SOURCE[4:19]
    assert not verify_verbatim(quote, SOURCE, 5, 20)


def test_verbatim_unicode_offsets_are_char_based():
    # slice across the emoji — char offsets, not bytes
    start = SOURCE.index("🏗")
    quote = SOURCE[start : start + 2]
    assert verify_verbatim(quote, SOURCE, start, start + 2)


def test_verbatim_rejects_bad_bounds():
    assert not verify_verbatim("x", SOURCE, -1, 3)
    assert not verify_verbatim("x", SOURCE, 0, len(SOURCE) + 1)
    assert not verify_verbatim("", SOURCE, 5, 5)  # start >= end


def test_inferred_edge_requires_rationale_and_two_highlights():
    assert not check_inferred_edge("inferred", None, 2)
    assert not check_inferred_edge("inferred", "because", 1)
    assert check_inferred_edge("inferred", "because", 2)


def test_asserted_edge_passes_without_rationale():
    assert check_inferred_edge("asserted", None, 0)


def test_view_block_rejects_dangling_refs():
    atoms = {"a1", "a2"}
    assert check_view_block_refs(atoms, ["a1", "a2"])
    assert not check_view_block_refs(atoms, ["a1", "ghost"])
