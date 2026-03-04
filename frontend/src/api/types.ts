export type PolicyListItem = {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  download_status: "success" | "failed" | "pending";
  has_structured_tree: boolean;
};

export type CriteriaNode = {
  rule_id: string;
  rule_text: string;
  operator?: "AND" | "OR";
  rules?: CriteriaNode[];
};

export type CriteriaTree = {
  title: string;
  insurance_name: string;
  rules: CriteriaNode;
};

export type PolicyDetail = {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  download_status: "success" | "failed" | "pending";
  latest_download?: {
    id: number;
    stored_location: string;
    downloaded_at: string;
    http_status?: number | null;
    error?: string | null;
  } | null;
  structured?: {
    id: number;
    policy_id: number;
    extracted_text: string;
    structured_json: CriteriaTree;
    structured_at: string;
    llm_model: string;
    llm_prompt: string;
    validation_error?: string | null;
  } | null;
};
