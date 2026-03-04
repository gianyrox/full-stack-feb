export interface RuleNode {
  rule_id: string;
  rule_text: string;
  operator?: "AND" | "OR";
  rules?: RuleNode[];
}

export interface StructuredPolicy {
  title: string;
  insurance_name: string;
  rules: RuleNode;
}

export interface Policy {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  has_structured: boolean;
}
