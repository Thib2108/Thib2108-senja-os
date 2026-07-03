"""Ontology binding contract — SDAI-CHAT-004 ADR-02.

Taxonomies and the Edge Registry are loaded as *versioned inputs* to every
worker — never baked into prompts. Every output stamps the version it bound to.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BindingContract:
    taxonomy_version: str
    edge_registry_version: str

    def stamp(self) -> dict[str, str]:
        """The provenance stamp every P2/P3/P4 output must carry."""
        return {
            "taxonomy_version": self.taxonomy_version,
            "edge_registry_version": self.edge_registry_version,
        }
