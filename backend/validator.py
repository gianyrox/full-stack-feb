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
    """
    try:
        StructuredPolicy.model_validate(data)
        return True, None
    except Exception as e:
        return False, str(e)


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
