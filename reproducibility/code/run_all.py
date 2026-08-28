#!/usr/bin/env python3
"""Execute the analysis notebooks and verify their reported results."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

import nbformat
import pandas as pd
from nbclient import NotebookClient

from build_recurrent_registry import build as build_registry, reader_view
from validate_release import validate


NOTEBOOKS = (
    "01_data_overview.ipynb",
    "02_manuscript_analyses.ipynb",
)


def execute_notebook(
    notebook_path: Path,
    executed_path: Path,
    package_root: Path,
    output_dir: Path,
) -> None:
    """Execute one notebook with the current Python interpreter."""

    with tempfile.TemporaryDirectory(prefix="atlas_kernel_") as temporary:
        temporary_path = Path(temporary)
        kernel_name = "atlas-v23"
        kernel_directory = temporary_path / "kernels" / kernel_name
        kernel_directory.mkdir(parents=True)
        (kernel_directory / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [
                        sys.executable,
                        "-m",
                        "ipykernel_launcher",
                        "-f",
                        "{connection_file}",
                    ],
                    "display_name": "Python 3 (Atlas v23)",
                    "language": "python",
                }
            ),
            encoding="utf-8",
        )

        previous = {
            name: os.environ.get(name)
            for name in ("JUPYTER_PATH", "ATLAS_PACKAGE_ROOT", "ATLAS_OUTPUT_DIR")
        }
        try:
            existing_jupyter_path = previous["JUPYTER_PATH"]
            os.environ["JUPYTER_PATH"] = (
                str(temporary_path)
                if not existing_jupyter_path
                else os.pathsep.join((str(temporary_path), existing_jupyter_path))
            )
            os.environ["ATLAS_PACKAGE_ROOT"] = str(package_root)
            os.environ["ATLAS_OUTPUT_DIR"] = str(output_dir)

            notebook = nbformat.read(notebook_path, as_version=4)
            client = NotebookClient(
                notebook,
                timeout=900,
                kernel_name=kernel_name,
                allow_errors=False,
            )
            client.execute(cwd=str(notebook_path.parent))
            for cell in notebook.cells:
                cell.metadata.pop("execution", None)
            nbformat.write(notebook, executed_path)
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


def locate(package_root: Path, filename: str) -> Path:
    candidates = [
        package_root / "data" / "analysis_inputs" / filename,
        package_root / "reproducibility" / "data" / "analysis_inputs" / filename,
        package_root / filename,
    ]
    found = [path for path in candidates if path.is_file()]
    if len(found) == 1:
        return found[0]
    if not found:
        searched = "\n  ".join(str(path) for path in candidates)
        raise FileNotFoundError(f"Could not find {filename}. Searched:\n  {searched}")
    raise ValueError(f"Found multiple copies of {filename}: {found}")


def canonical_registry(package_root: Path) -> Path | None:
    candidates = [
        package_root
        / "reproducibility"
        / "data"
        / "aggregate_data"
        / "Recurrent_Candidate_Registry.csv",
        package_root / "data" / "derived_registry" / "Recurrent_Candidate_Registry.csv",
        package_root
        / "reproducibility"
        / "data"
        / "derived_registry"
        / "Recurrent_Candidate_Registry.csv",
        package_root / "Recurrent_Candidate_Registry.csv",
    ]
    found = [path for path in candidates if path.is_file()]
    if len(found) > 1:
        raise ValueError(
            f"Found multiple registries for candidates identified repeatedly: {found}"
        )
    return found[0] if found else None


def reader_registry(package_root: Path) -> Path | None:
    path = package_root / "supplement" / "Recurrent_Candidate_Registry.csv"
    return path if path.is_file() else None


def optional_registry_memberships(package_root: Path) -> Path | None:
    candidates = [
        package_root
        / "reproducibility"
        / "data"
        / "analysis_inputs"
        / "Recurrent_Candidate_Qualifying_Memberships.csv",
        package_root / "data" / "analysis_inputs" / "Recurrent_Candidate_Qualifying_Memberships.csv",
    ]
    found = [path for path in candidates if path.is_file()]
    if len(found) > 1:
        raise ValueError(
            f"Found multiple files containing observations of qualifying candidates: {found}"
        )
    return found[0] if found else None


def optional_registry_citations(package_root: Path) -> Path | None:
    candidates = [
        package_root / "supplement" / "Recurrent_Candidate_Source_Citations.csv",
        package_root / "Recurrent_Candidate_Source_Citations.csv",
    ]
    found = [path for path in candidates if path.is_file()]
    if len(found) > 1:
        raise ValueError(
            f"Found multiple source-citation files for candidates identified repeatedly: {found}"
        )
    return found[0] if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    package_root = args.package_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    recurrence_input = locate(package_root, "Recurrence_Analysis_Matrix_Anonymous.csv")
    fixed_margin_input = locate(package_root, "Fixed_Margin_Comparison_Blocks.csv")
    registry = canonical_registry(package_root)
    released_reader_registry = reader_registry(package_root)
    registry_memberships = optional_registry_memberships(package_root)
    registry_citations = optional_registry_citations(package_root)

    code_dir = Path(__file__).resolve().parent
    for notebook_name in NOTEBOOKS:
        notebook_path = code_dir / notebook_name
        if not notebook_path.is_file():
            raise FileNotFoundError(f"Required notebook is absent: {notebook_path}")
        executed_path = output_dir / notebook_name.replace(
            ".ipynb", ".executed.ipynb"
        )
        execute_notebook(
            notebook_path,
            executed_path,
            package_root,
            output_dir,
        )
    if registry is not None and registry_memberships is not None:
        if registry_citations is None:
            raise FileNotFoundError(
                "Observations of qualifying candidates require the source-citation table"
            )
        rebuilt = build_registry(registry_memberships, registry_citations)
        rebuilt_path = output_dir / "reconstructed_recurrent_candidate_registry.csv"
        rebuilt.to_csv(rebuilt_path, index=False)
        canonical = pd.read_csv(registry, dtype=str, keep_default_na=False)
        comparison_columns = [
            "canonical_identity_key",
            "normalized_accession_or_line_id",
            "recurrence_pattern",
            "qualifying_evidence_set_n",
            "qualifying_evidence_set_ids",
            "disease_categories",
            "same_disease_recurrence_categories",
            "source_ids",
        ]
        canonical_core = canonical[comparison_columns].sort_values(
            "canonical_identity_key"
        ).reset_index(drop=True)
        rebuilt_core = rebuilt[comparison_columns].astype(str).sort_values(
            "canonical_identity_key"
        ).reset_index(drop=True)
        if not canonical_core.equals(rebuilt_core):
            raise AssertionError(
                "Reconstructed and released detailed registries differ"
            )
        rebuilt_reader = reader_view(rebuilt)
        rebuilt_reader_path = (
            output_dir / "reconstructed_recurrent_candidate_registry_for_readers.csv"
        )
        rebuilt_reader.to_csv(rebuilt_reader_path, index=False)
        if released_reader_registry is None:
            raise FileNotFoundError(
                "Expected supplementary registry for candidates identified repeatedly"
            )
        released_reader = pd.read_csv(
            released_reader_registry, dtype=str, keep_default_na=False
        )
        rebuilt_reader_text = rebuilt_reader.astype(str)
        if not released_reader.equals(rebuilt_reader_text):
            raise AssertionError(
                "Reconstructed and released supplementary candidate tables differ"
            )
    validation = validate(
        recurrence_input,
        fixed_margin_input,
        output_dir,
        registry,
        registry_memberships,
        package_root,
    )
    (output_dir / "analysis_validation.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(validation, sort_keys=True))
    return 0 if validation["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
