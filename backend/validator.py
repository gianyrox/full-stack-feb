from __future__ import annotations

import json
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, model_validator


class RuleNode(BaseModel):
    rule_id: str
    rule_text: str
    operator: Optional[Literal["AND", "OR"]] = None
    rules: Optional[List[RuleNode]] = None

    @model_validator(mode="after")
    def check_operator_rules_consistency(self) -> "RuleNode":
        has_operator = self.operator is not None
        has_rules = self.rules is not None
        if has_operator and not has_rules:
            raise ValueError(
                f"Node '{self.rule_id}' has 'operator' but no 'rules' array"
            )
        if has_rules and not has_operator:
            raise ValueError(
                f"Node '{self.rule_id}' has 'rules' array but no 'operator'"
            )
        return self


RuleNode.model_rebuild()


class StructuredPolicy(BaseModel):
    title: str
    insurance_name: str
    rules: RuleNode


def validate_structured_json(data: dict) -> Tuple[bool, Optional[str]]:
    """Validate a dict against the StructuredPolicy schema.

    Returns (True, None) on success or (False, error_message) on failure.
    Performs both Pydantic schema validation and logical tree traversal.
    """
    # 1. Pydantic schema validation
    try:
        StructuredPolicy.model_validate(data)
    except Exception as e:
        return False, str(e)

    # 2. Logical tree traversal (DFS)
    warnings: List[str] = []
    try:
        _traverse_and_validate(data.get("rules", {}), "", 1, set(), warnings)
    except ValueError as e:
        return False, str(e)

    if warnings:
        return True, "Warnings: " + "; ".join(warnings)

    return True, None


def _traverse_and_validate(
    node: dict,
    parent_prefix: str,
    depth: int,
    seen_ids: set,
    warnings: List[str],
) -> None:
    """DFS traversal to validate tree logic beyond schema."""
    rule_id = node.get("rule_id", "")
    rule_text = node.get("rule_text", "")

    # Empty text check
    if not rule_text.strip():
        raise ValueError(f"Empty rule_text at node {rule_id}")

    # Depth warning
    if depth > 5:
        warnings.append(f"Depth {depth} at {rule_id} (possible hallucination)")

    # Unique rule_id
    if rule_id in seen_ids:
        raise ValueError(f"Duplicate rule_id: {rule_id}")
    seen_ids.add(rule_id)

    # Hierarchy prefix check (skip root "1")
    if rule_id != "1" and parent_prefix:
        if not rule_id.startswith(parent_prefix + "."):
            warnings.append(f"Hierarchy break: {rule_id} not child of {parent_prefix}")

    # Operator consistency with text
    has_rules = "rules" in node and isinstance(node.get("rules"), list) and len(node["rules"]) > 0
    if has_rules:
        op = node.get("operator", "")
        text_lower = rule_text.lower()
        if "all of the following" in text_lower and op != "AND":
            warnings.append(f"{rule_id} implies ALL but operator is {op}")
        if "one of the following" in text_lower and op != "OR":
            warnings.append(f"{rule_id} implies ONE but operator is {op}")

        # Sequential child ID check
        for i, child in enumerate(node["rules"], start=1):
            expected = f"{rule_id}.{i}"
            actual = child.get("rule_id", "")
            if actual != expected:
                warnings.append(f"Sequential gap: got {actual}, expected {expected}")
            _traverse_and_validate(child, rule_id, depth + 1, seen_ids, warnings)


if __name__ == "__main__":
    import pathlib

    oscar_path = pathlib.Path(__file__).resolve().parent.parent / "oscar.json"
    with open(oscar_path) as f:
        data = json.load(f)

    is_valid, error = validate_structured_json(data)
    if is_valid:
        print("oscar.json is valid.")
    else:
        print(f"oscar.json is invalid: {error}")
