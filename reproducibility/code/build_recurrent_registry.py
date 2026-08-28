#!/usr/bin/env python3
"""Rebuild the registries for the 171 repeatedly identified candidates."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


MEMBERSHIP_COLUMNS = {
    "normalized_accession_or_line_id",
    "canonical_identity_key",
    "identity_basis",
    "reported_label",
    "evidence_set_id",
    "disease_categories",
    "source_registry_ids",
}
CITATION_COLUMNS = {
    "source_registry_id",
    "citation_key",
    "full_citation",
    "landing_page_url",
    "redistribution_status",
}


def split_values(value: object) -> list[str]:
    return sorted(
        {
            item.strip()
            for item in str(value).replace("||", "|").split("|")
            if item.strip()
        }
    )


def build(memberships_path: Path, citations_path: Path) -> pd.DataFrame:
    memberships = pd.read_csv(memberships_path, dtype=str, keep_default_na=False)
    citations = pd.read_csv(citations_path, dtype=str, keep_default_na=False)
    missing_membership = sorted(MEMBERSHIP_COLUMNS - set(memberships.columns))
    missing_citation = sorted(CITATION_COLUMNS - set(citations.columns))
    if missing_membership or missing_citation:
        raise ValueError(
            f"Missing columns; memberships={missing_membership}, citations={missing_citation}"
        )
    citation_key = citations.set_index("source_registry_id")
    rows: list[dict[str, object]] = []

    for normalized_id, group in memberships.groupby(
        "normalized_accession_or_line_id", sort=True
    ):
        canonical = sorted(set(group["canonical_identity_key"]))
        identity_bases = sorted(set(group["identity_basis"]))
        if len(canonical) != 1 or len(identity_bases) != 1:
            raise ValueError(
                f"Accession or line labels are inconsistent for {normalized_id}"
            )

        evidence_sets = sorted(set(group["evidence_set_id"]))
        reported_labels = sorted(
            {value.strip() for value in group["reported_label"] if value.strip()}
        )
        disease_to_sets: dict[str, set[str]] = {}
        for row in group.itertuples(index=False):
            for disease in split_values(row.disease_categories):
                disease_to_sets.setdefault(disease, set()).add(row.evidence_set_id)
        same_diseases = sorted(
            disease for disease, sets in disease_to_sets.items() if len(sets) >= 2
        )
        pattern = "same_disease_recurrence" if same_diseases else "cross_disease_only"

        source_ids = sorted(
            {
                source_id
                for value in group["source_registry_ids"]
                for source_id in split_values(value)
            }
        )
        missing_sources = sorted(set(source_ids) - set(citation_key.index))
        if missing_sources:
            raise ValueError(f"Missing citations for {missing_sources}")
        source_rows = citation_key.loc[source_ids]
        if isinstance(source_rows, pd.Series):
            source_rows = source_rows.to_frame().T

        doi_tokens = []
        provenance_tokens = []
        for source_id in source_ids:
            source_row = citation_key.loc[source_id]
            identifiers = [
                value
                for value in (
                    str(source_row["article_doi"]).strip(),
                    str(source_row["repository_doi"]).strip(),
                )
                if value
            ]
            doi_tokens.append(
                "|".join(identifiers)
                if identifiers
                else f"URL:{str(source_row['landing_page_url']).strip()}"
            )
            provenance_tokens.append(
                ":".join(
                    str(source_row[column]).strip()
                    for column in (
                        "source_checksum_status",
                        "license_status",
                        "redistribution_status",
                    )
                )
            )

        rows.append(
            {
                "normalized_accession_or_line_id": normalized_id,
                "canonical_identity_key": canonical[0],
                "identity_basis": identity_bases[0],
                "reported_label_variants": " | ".join(reported_labels),
                "recurrence_pattern": pattern,
                "qualifying_evidence_set_n": len(evidence_sets),
                "qualifying_evidence_set_ids": " | ".join(evidence_sets),
                "disease_categories": " | ".join(sorted(disease_to_sets)),
                "same_disease_recurrence_categories": " | ".join(same_diseases),
                "qualifying_source_n": len(source_ids),
                "source_ids": " | ".join(source_ids),
                "source_citation_keys": " | ".join(source_rows["citation_key"]),
                "source_citations": " || ".join(source_rows["full_citation"]),
                "source_urls": " | ".join(source_rows["landing_page_url"]),
                "source_doi_or_repository_ids": " | ".join(doi_tokens),
                "source_redistribution_statuses": " | ".join(
                    source_rows["redistribution_status"]
                ),
                "source_provenance_statuses": " | ".join(provenance_tokens),
            }
        )

    result = pd.DataFrame(rows).sort_values(
        ["recurrence_pattern", "normalized_accession_or_line_id"]
    ).reset_index(drop=True)
    patterns = result["recurrence_pattern"].value_counts()
    if len(result) != 171 or patterns.to_dict() != {
        "cross_disease_only": 93,
        "same_disease_recurrence": 78,
    }:
        raise AssertionError(
            f"Unexpected registry totals: candidates={len(result)}, patterns={patterns.to_dict()}"
        )
    distribution = result["qualifying_evidence_set_n"].value_counts().to_dict()
    if distribution != {2: 164, 3: 7}:
        raise AssertionError(
            f"Expected 164 candidates in two independent screens and 7 in three; found {distribution}"
        )
    return result


def reader_view(registry: pd.DataFrame) -> pd.DataFrame:
    """Return the concise, shareable registry supplied with the supplement."""

    required = {
        "normalized_accession_or_line_id",
        "reported_label_variants",
        "recurrence_pattern",
        "qualifying_evidence_set_n",
        "disease_categories",
        "same_disease_recurrence_categories",
        "source_citations",
        "source_urls",
    }
    missing = sorted(required - set(registry.columns))
    if missing:
        raise ValueError(
            f"The detailed registry lacks columns required for the supplementary table: {missing}"
        )

    def readable_diseases(value: object) -> str:
        return "; ".join(
            item.replace("_", " ") for item in split_values(value)
        )

    result = pd.DataFrame(
        {
            "Normalized accession or line ID": registry[
                "normalized_accession_or_line_id"
            ],
            "Reported label(s)": registry["reported_label_variants"].str.replace(
                " | ", "; ", regex=False
            ),
            "Repeated identification pattern": registry["recurrence_pattern"].map(
                {
                    "same_disease_recurrence": "Same disease",
                    "cross_disease_only": "Different diseases only",
                }
            ),
            "Number of qualifying independent screens": pd.to_numeric(
                registry["qualifying_evidence_set_n"], errors="raise"
            ).astype(int),
            "Diseases represented": registry["disease_categories"].map(
                readable_diseases
            ),
            "Disease repeated in more than one screen": registry[
                "same_disease_recurrence_categories"
            ].map(readable_diseases).replace("", "No disease repeated"),
            "Source citations": registry["source_citations"].str.replace(
                " || ", "; ", regex=False
            ),
            "Source links": registry["source_urls"].str.replace(
                " | ", "; ", regex=False
            ),
        }
    )
    if result["Repeated identification pattern"].isna().any():
        raise ValueError(
            "The detailed registry contains an unexpected repeated identification category"
        )
    if len(result) != 171:
        raise AssertionError(
            f"Supplementary registry expected 171 candidates, found {len(result)}"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memberships", type=Path, required=True)
    parser.add_argument("--citations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--reader-output",
        type=Path,
        help="Optional concise CSV for readers of the supplement",
    )
    args = parser.parse_args()
    result = build(args.memberships, args.citations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"PASS: wrote {len(result)} repeatedly identified candidates to {args.output}")
    if args.reader_output is not None:
        args.reader_output.parent.mkdir(parents=True, exist_ok=True)
        reader_view(result).to_csv(args.reader_output, index=False)
        print(f"PASS: wrote the concise registry to {args.reader_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
