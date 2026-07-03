"""Versioned binding-contract input — SDAI-CHAT-004 ADR-02.

Loads facet schemes + the Edge Registry as versioned inputs to every P2/P3/P4
worker. Every output stamps the version it bound to (CI: ontology-version gate).
"""

from harness_kernel.binding import BindingContract

from contracts.edges import EDGE_REGISTRY_VERSION


def load_binding() -> BindingContract:  # TODO(004-slice): load taxonomy version from generated contracts
    return BindingContract(taxonomy_version="0.0.0-pre", edge_registry_version=EDGE_REGISTRY_VERSION)
