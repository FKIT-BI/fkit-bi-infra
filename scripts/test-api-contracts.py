#!/usr/bin/env python3
"""Structural lint for every checked-in OpenAPI contract used by FKIT BI."""

from pathlib import Path
import sys

import yaml
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parents[1]


def repository_contract(repository, filename):
    candidates = (
        ROOT.parent / repository / "docs/contracts" / filename,
        ROOT / ".ci" / repository / "docs/contracts" / filename,
    )
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


CONTRACTS = (
    ROOT / "docs/contracts/auth-api.yaml",
    repository_contract("fkit-bi-analytics", "analytics-api-draft.yaml"),
    repository_contract("fkit-bi-analytics", "draft-api.yaml"),
    repository_contract("fkit-bi-generator", "generator-api-draft.yaml"),
)
EXPECTED_OPERATION_COUNTS = {
    "auth-api.yaml": 2,
    "analytics-api-draft.yaml": 67,
    "draft-api.yaml": 28,
    "generator-api-draft.yaml": 12,
}
METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def resolve_pointer(document, pointer, source):
    if not pointer.startswith("#/"):
        raise ValueError(f"{source}: external/non-local reference is not allowed: {pointer}")
    target = document
    for part in pointer[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(target, list):
            target = target[int(part)]
        elif isinstance(target, dict) and part in target:
            target = target[part]
        else:
            raise ValueError(f"{source}: unresolved reference {pointer}")
    return target


def walk_refs(document, value, source):
    if isinstance(value, dict):
        reference = value.get("$ref")
        if reference is not None:
            resolve_pointer(document, reference, source)
        for child in value.values():
            walk_refs(document, child, source)
    elif isinstance(value, list):
        for child in value:
            walk_refs(document, child, source)


def lint(path):
    source = (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else f"{path.parents[2].name}/docs/contracts/{path.name}"
    )
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    validate(document)
    if not isinstance(document, dict) or document.get("openapi") != "3.1.0":
        raise ValueError(f"{source}: expected an OpenAPI 3.1.0 document")
    if not isinstance(document.get("info"), dict) or not document["info"].get("title"):
        raise ValueError(f"{source}: info.title is required")
    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise ValueError(f"{source}: paths must be a non-empty mapping")
    schemes = document.get("components", {}).get("securitySchemes", {})
    if document.get("security") and "bearerAuth" not in schemes:
        raise ValueError(f"{source}: global security requires a shared bearerAuth scheme")

    operation_ids = set()
    operation_count = 0
    for path_name, path_item in paths.items():
        if not isinstance(path_item, dict):
            raise ValueError(f"{source}: {path_name} must be a path item")
        for method, operation in path_item.items():
            if method.lower() not in METHODS:
                continue
            if not isinstance(operation, dict):
                raise ValueError(f"{source}: {method.upper()} {path_name} must be an operation")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ValueError(f"{source}: {method.upper()} {path_name} is missing operationId")
            if operation_id in operation_ids:
                raise ValueError(f"{source}: duplicate operationId {operation_id}")
            operation_ids.add(operation_id)
            responses = operation.get("responses")
            if not isinstance(responses, dict) or not any(str(code).startswith("2") for code in responses):
                raise ValueError(f"{source}: {operation_id} must document a success response")
            operation_count += 1
    if not operation_count:
        raise ValueError(f"{source}: no HTTP operations found")
    expected_count = EXPECTED_OPERATION_COUNTS.get(path.name)
    if expected_count is not None and operation_count != expected_count:
        raise ValueError(f"{source}: expected {expected_count} operations, found {operation_count}")
    walk_refs(document, document, source)
    return operation_count


def main():
    total = 0
    for contract in CONTRACTS:
        if not contract.is_file():
            raise ValueError(f"missing OpenAPI contract: {contract}")
        count = lint(contract)
        total += count
        source = (
            contract.relative_to(ROOT).as_posix()
            if contract.is_relative_to(ROOT)
            else f"{contract.parents[2].name}/docs/contracts/{contract.name}"
        )
        print(f"OpenAPI OK: {source} ({count} operations)")
    print(f"OpenAPI structural lint passed: {len(CONTRACTS)} contracts, {total} operations")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"OpenAPI contract lint failed: {error}", file=sys.stderr)
        sys.exit(1)
