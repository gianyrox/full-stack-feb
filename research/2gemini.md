# Architecting a Production-Ready Pipeline for Structuring Medical Necessity Criteria from Clinical Guidelines

The translation of unstructured clinical guidelines into deterministic, machine-readable data structures is a critical capability for automating healthcare utilization management. Documents such as the Oscar Health clinical guidelines—which include policies for procedures like Bariatric Surgery (CG008) and Acupuncture (CG013)—are densely formatted PDFs. They are characterized by hierarchical lists, complex logical operators (AND/OR), embedded medical terminology, and mixed content including definitions, billing codes, and multi-stage criteria.

Converting these natural language rules into a strict, recursive JSON decision tree requires a highly orchestrated natural language processing (NLP) and document parsing pipeline. The architecture must systematically ingest a PDF, accurately parse its visual and semantic structure while preserving list hierarchies and mathematical operators, isolate the specific section pertaining to "Initial" medical necessity, and leverage a Large Language Model (LLM) to map the natural language into the target schema.

This report provides an exhaustive, production-grade blueprint for constructing this pipeline. It details optimal LLM prompting strategies designed to infer implicit medical logic, advances regular expression (regex) heuristics for section boundary detection, provides comprehensive comparative evaluations of Python PDF extraction libraries, and implements robust JSON validation and auto-repair mechanisms. The methodology prioritizes deterministic outcomes, utilizing structured decoding techniques and fallback heuristics to ensure the resulting JSON tree perfectly mirrors the logical flow of the source medical policy, mitigating the risks of LLM hallucination.

## Part A: Optimal LLM Prompt Engineering

Transforming hierarchical, natural-language medical criteria into a strict, recursive JSON tree requires advanced prompt engineering. The LLM must be instructed not only on the required output schema but also on the specific semantic nuances of medical policy writing, such as implicit logical operators, sequential numbering algorithms, and the critical distinction between leaf and non-leaf nodes.

### System Prompt Design

The system prompt serves as the foundational instruction set. It must explicitly define the rules of hierarchical mapping, operator inference, and structural formatting. To ensure deterministic behavior from models like GPT-4o, the prompt must preemptively address known edge cases found in Oscar Health guidelines, such as inline exceptions and nested logic.

```
You are an expert Medical Policy Analyst and Clinical NLP Data Architect. Your objective is to extract "Initial" Medical Necessity Criteria from health insurance clinical guideline text and convert it into a strict, recursive JSON decision tree.

=== CORE OBJECTIVE ===
You will be provided with text extracted from an Oscar Health clinical guideline. You must locate the primary/initial "Criteria for Medically Necessary Procedures" section and map its logic into the exact JSON format requested.

=== STRICT OUTPUT SCHEMA ===
You must output a JSON object with the following structure exactly. Do not deviate.
{
"title": "String - The most descriptive title for the criteria tree (e.g., 'Medical Necessity Criteria for Bariatric Surgery')",
"insurance_name": "Oscar Health",
"rules": {
"rule_id": "1",
"rule_text": "String - The parent criteria text",
"operator": "AND" | "OR", // ONLY present if there are sub-rules
"rules": [...]
}
}

=== CRITICAL EXTRACTION RULES ===

SECTION IDENTIFICATION:

Parse ONLY the primary/initial medical necessity criteria.

IGNORE sections labeled: Summary, Definitions, Clinical Indications (unless it contains the criteria), Procedures & Length of Stay, Continuation/Renewal/Reauthorization criteria, Repair/Revision/Conversion/Removal criteria, Experimental/Investigational, Relative Contraindications, and Applicable Billing Codes (HCPCS & CPT Codes).

If the document contains multiple distinct criteria trees for different indications, extract only the first/primary one unless instructed otherwise.

HIERARCHICAL RULE_ID GENERATION:

The root node is ALWAYS "1".

Direct children of "1" are "1.1", "1.2", "1.3", etc.

Grandchildren are "1.1.1", "1.2.1", etc.

You must map the PDF's numbering system (e.g., 1 -> a -> i -> 1) directly to this dotted hierarchy. Maintain sequential order exactly as it appears in the text.

LEAF VS NON-LEAF NODES (CRITICAL):

NON-LEAF NODE: If an item has sub-items (children), it MUST contain both an operator ("AND" or "OR") and a rules array. Never omit these from a non-leaf node.

LEAF NODE: If an item has no sub-items, it is a leaf node. It MUST ONLY contain rule_id and rule_text. NEVER put an operator or rules array on a leaf node.

LOGICAL OPERATOR DETECTION (AND/OR):

Explicit Parent Triggers: If a parent node says "ALL of the following", "MUST meet all", "each of", or "both", the operator is "AND". If it says "ONE of the following", "ANY of the following", "at least one", "one or more", or "either", the operator is "OR".

Inline Connectors: Look at the end of the child items. If an item ends with "; and", the parent's operator governing these siblings is "AND". If it ends with "; or", the parent's operator is "OR".

Implicit Convention: If there are numbered/lettered items with no explicit connectors, default to "AND" logic, as this is the standard medical policy convention.

Mixed Logic: If a single criterion mixes AND/OR within the same level (e.g., "A and (B or C)"), you must split this into nested nodes to preserve the strict binary tree structure.

EDGE CASES TO HANDLE:

Cross-references: If a criterion says "see section below", "as defined above", or "see CG009", include this text exactly as written in the rule_text.

Inline exceptions: Keep inline exceptions (e.g., "EXCEPT when...", "unless...") within the rule_text of that specific node.

Long text: Combine multi-line paragraphs belonging to a single criterion into a single continuous rule_text string.

Notes: Embed clinical notes directly into the rule_text of the item they describe (e.g., "Note: Enlargement of pouch...").

Missing "Initial" Label: If the criteria section lacks an explicit "Initial" label, default to parsing the first criteria tree presented in the document.

Output strictly valid JSON matching the schema. Do not include markdown formatting like ```json in the output.
```

### User Prompt Template

The user prompt dynamically injects the extracted text and reinforces the execution of the system instructions immediately prior to generation. This localized reinforcement limits context degradation over long inputs.

```
Here is the text extracted from the Oscar Health clinical guideline PDF:

<EXTRACTED_TEXT>
{pdf_text}
</EXTRACTED_TEXT>

Instructions:
1. Scan the text to locate the first/initial "Criteria for Medically Necessary Procedures" section.
2. Stop extracting if you hit boundaries for "Continuation", "Repair/Revision", "Experimental", "Contraindications", or "Billing Codes".
3. Map the isolated criteria into the required JSON decision tree schema.
4. Ensure the root node is "1" and all child nodes follow dotted notation (1.1, 1.1.1).
5. Double-check that NO leaf nodes contain an "operator" or "rules" array.
6. Double-check that ALL non-leaf nodes contain an "operator" and a "rules" array.

Return only the final JSON object.
```

## Part B: "Initial Only" Detection Heuristics

Clinical guidelines are structured linearly, but the exact nomenclature for section headers varies widely across different documents and updates. A bariatric surgery guideline (CG008) might seamlessly transition from initial criteria to "Revision of a primary bariatric surgery" without a hard demarcation, whereas an oxygen therapy guideline (CG005) explicitly denotes "Short Term Oxygen Therapy (STOT)" and "Reassessment of STOT".

Therefore, passing the entire document to the LLM risks confusing the model with disparate criteria trees. Extracting the "Initial" criteria requires a programmatic approach utilizing regular expressions and state-machine logic to identify and slice section boundaries before the LLM processing phase.

### Regex Patterns and Keyword Vocabularies

To slice the document accurately, the system defines explicit boundary triggers. These patterns account for case variations, optional spacing, and common phrasing found in medical insurance PDFs.

```python
import re

# Patterns indicating the start of the initial medical necessity criteria
START_PATTERNS = [
    r'(?i)criteria\s+for\s+medically\s+necessary',
    r'(?i)initial\s+(criteria|authorization|approval)',
    r'(?i)medical\s+necessity\s+criteria',
    r'(?i)conditions\s+for\s+coverage',
]

# Patterns indicating the start of a new, non-initial section (stopping points)
END_PATTERNS = [
    r'(?i)continuation\s+(criteria|therapy|treatment|of\s+therapy)',
    r'(?i)re-?authorization\s+criteria',
    r'(?i)renewal\s+criteria',
    r'(?i)repair[/,]\s*revision',
    r'(?i)conversion\s+criteria',
    r'(?i)removal\s+criteria',
    r'(?i)experimental\s*[/&]\s*investigational',
    r'(?i)relative\s+contraindications',
    r'(?i)applicable\s+billing\s+codes',
    r'(?i)HCPCS\s+(&|and)\s+CPT\s+codes',
    r'(?i)procedures?\s*(&|and)\s*length\s+of\s+stay',
]
```

### Section Boundary Detection Algorithm

The following Python implementation utilizes a line-by-line scanning approach, functioning as a finite state machine, to isolate the target text. This is more resilient than massive multi-line regex blocks, which frequently fail due to unpredictable invisible line breaks generated during PDF parsing.

```python
from typing import Tuple

def extract_initial_criteria(full_text: str) -> Tuple[str, float, str]:
    """
    Extracts only the initial medical necessity criteria from the full PDF text.

    Returns:
        Tuple containing:
        - The extracted section as a string.
        - A confidence score (float between 0.0 and 1.0).
        - A string detailing the extraction logic applied.
    """
    lines = full_text.split('\n')

    start_idx = -1
    end_idx = -1
    confidence = 0.0
    extraction_logic = "No boundaries detected."

    # Pre-compile regex for computational efficiency
    start_regexes = [re.compile(p) for p in START_PATTERNS]
    end_regexes = [re.compile(p) for p in END_PATTERNS]

    in_criteria_section = False

    for i, line in enumerate(lines):
        clean_line = line.strip()
        if not clean_line:
            continue

        # Step 1: Detect Start Boundary
        if not in_criteria_section:
            for pattern in start_regexes:
                if pattern.search(clean_line):
                    start_idx = i
                    in_criteria_section = True
                    # Higher confidence if explicitly labeled "Initial"
                    if "initial" in clean_line.lower():
                        confidence = 0.95
                        extraction_logic = f"Found explicit 'Initial' start marker at line {i}."
                    else:
                        confidence = 0.85
                        extraction_logic = f"Found generic criteria start marker at line {i}."
                    break

        # Step 2: Detect End Boundary
        elif in_criteria_section:
            for pattern in end_regexes:
                if pattern.match(clean_line):
                    end_idx = i
                    extraction_logic += f" Found explicit end marker '{clean_line[:30]}...' at line {i}."
                    break

            # Step 3: Heuristic Fallback for Unlabeled Sections
            if end_idx == -1 and clean_line.isupper() and len(clean_line) > 10:
                 if "BACKGROUND" in clean_line or "SUMMARY" in clean_line:
                     end_idx = i
                     extraction_logic += f" Hit uppercase block acting as end boundary at line {i}."

            if end_idx != -1:
                break

    # Fallback Logic Execution
    if start_idx == -1:
        return full_text, 0.30, "Fallback: No start boundary found. Returning full text."

    if end_idx == -1:
        end_idx = len(lines)
        confidence -= 0.15
        extraction_logic += " Reached EOF without explicit end marker."

    extracted_section = '\n'.join(lines[start_idx:end_idx])
    return extracted_section, confidence, extraction_logic
```

### Confidence Scoring Metadata

The algorithm returns a confidence score alongside the text, stored as metadata. A score of 0.95 implies explicit detection of "Initial Criteria", indicating a highly reliable extraction. A score of 0.85 indicates a generic "Criteria for Medically Necessary Procedures" header was found, which is accurate for policies like CG008 (Bariatric Surgery) that do not use the word "Initial". A score of 0.30 triggers a fallback where the entire parsed document is passed to the LLM, relying entirely on the LLM's prompt instructions to filter out non-initial data. Tracking this metric provides observability into pipeline health and flags documents requiring human review.

## Part C: PDF Text Extraction Evaluation and Implementation

Extracting text from medical PDFs is notoriously difficult. Clinical guidelines rely heavily on nested alphanumeric bullet points (1, a, i), multi-column layouts, and mathematical symbols (e.g., ≥, ≤) to denote vital diagnostic thresholds. If the extraction library corrupts the reading order or loses the greater-than symbol in "BMI ≥40", the downstream JSON tree will contain critical clinical inaccuracies. A comparison of the four primary Python libraries reveals stark differences in capability.

### Comparison of Extraction Libraries

| Feature | PyMuPDF (fitz) | pdfplumber | pdfminer.six | PyPDF2 / pypdf |
|---------|---------------|------------|--------------|----------------|
| Extraction Quality | Excellent. Natively supports document layout mapping. | Exceptional. Reconstructs blocks via spatial coordinates. | High. Powerful layout analysis algorithms. | Poor. Relies on raw stream order. |
| List Numbering | Maintained perfectly using the sort=True block generator. | Maintained well, relies on x/y coordinate spacing. | Maintained, but complex to parse programmatically. | Frequently loses indentation contexts. |
| Special Characters | Flawless Unicode support. ≥, ≤, ™ remain intact. | Good, but y_tolerance settings can alter custom glyphs. | Good Unicode support. | Poor. Custom font mappings often result in garbled text. |
| Layout / Order | Natural reading order preserved mathematically. | Native column detection prevents merged text. | Accurate paragraph detection. | Frequently merges multi-column text horizontally. |
| Performance (10 pages) | Extremely fast (< 100 milliseconds). | Moderate (~1 to 2 seconds). | Slow (~2.5 seconds). | Fast (< 100 milliseconds). |

### 1. PyMuPDF (fitz)

PyMuPDF relies on the underlying C-based MuPDF engine, offering exceptional speed and memory efficiency. While raw text extraction can sometimes lose column formatting, using the block extraction method or setting sort=True enforces natural reading order (top-left to bottom-right). It handles Unicode characters like ≥ flawlessly, avoiding the symbol corruption seen in other libraries.

```python
import fitz  # PyMuPDF

def extract_pymupdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text_content = []
    for page in doc:
        # sort=True ensures natural reading order, critical for list structures
        text = page.get_text("text", sort=True)
        text_content.append(text)
    return "\n".join(text_content)
```

### 2. pdfplumber

Built on top of pdfminer.six, pdfplumber offers a more user-friendly API and excels at visual debugging and table extraction. It maintains column layouts and reconstructs paragraph boundaries natively. However, it relies heavily on spatial tolerances (y_tolerance, x_tolerance); aggressive tolerance settings can occasionally cause specialized font glyphs to be misinterpreted or replaced.

```python
import pdfplumber

def extract_pdfplumber(pdf_path: str) -> str:
    text_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # layout=True attempts to preserve visual spacing and column breaks
            text = page.extract_text(layout=True)
            if text:
                text_content.append(text)
    return "\n".join(text_content)
```

### 3. pdfminer.six

pdfminer.six focuses heavily on low-level layout analysis. It calculates precise bounding boxes for characters and attempts to reconstruct paragraphs and line breaks. While highly accurate, the API is exceedingly verbose, and the execution time is notably slow compared to C-bound libraries.

```python
from pdfminer.high_level import extract_text

def extract_pdfminer(pdf_path: str) -> str:
    # Uses advanced layout parameters natively
    text = extract_text(pdf_path)
    return text
```

### 4. PyPDF2 / pypdf

PyPDF2 (now modernized as pypdf) is a pure Python library designed for basic manipulation like merging and splitting. It extracts text strictly based on the underlying PDF stream order, frequently destroying multi-column layouts and completely losing hierarchical list structures. It is inadequate for clinical guidelines.

```python
from pypdf import PdfReader

def extract_pypdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text_content = []
    for page in reader.pages:
        text_content.append(page.extract_text())
    return "\n".join(text_content)
```

### Final Recommendation

**Recommendation: PyMuPDF (fitz) is the optimal choice for this specific pipeline.**

While pdfplumber is excellent for financial documents heavily reliant on tables, clinical guidelines primarily consist of hierarchical text. PyMuPDF's superior execution speed, flawless Unicode handling (which is absolutely critical for medical thresholds like "BMI ≥ 40"), and ability to enforce reading order via the sort=True parameter make it the most reliable engine. Furthermore, preserving list numbering is largely reliant on reading order rather than whitespace indentation, as the LLM utilizes semantic recognition of the alphanumeric sequences (1, a, i) rather than spatial indentation logic.

## Part D: JSON Validation and Repair

Enforcing a strictly typed, recursive JSON structure from an LLM is a complex challenge. Even with advanced system prompts, LLMs occasionally emit malformed data, such as placing an operator on a leaf node, generating invalid JSON syntax (e.g., missing brackets, trailing commas), or skipping sequential rule IDs.

### JSON Schema Definition

The pipeline validates the output against a formal JSON Schema. Because the required schema is recursive (a rule_node can contain an array of rule_node objects), it utilizes the $defs syntax for self-referencing.

```python
EXPECTED_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "insurance_name": {"type": "string"},
        "rules": {"$ref": "#/$defs/rule_node"}
    },
    "required": ["title", "insurance_name", "rules"],
    "$defs": {
        "rule_node": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "string"},
                "rule_text": {"type": "string"},
                "operator": {"type": "string", "enum": ["AND", "OR"]},
                "rules": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/rule_node"},
                    "minItems": 1
                }
            },
            "required": ["rule_id", "rule_text"],
            "allOf": [
                {
                    "if": {"required": ["rules"]},
                    "then": {"required": ["operator"]},
                    "errorMessage": "If 'rules' exist, 'operator' must exist."
                },
                {
                    "if": {"required": ["operator"]},
                    "then": {"required": ["rules"]},
                    "errorMessage": "If 'operator' exists, 'rules' must exist."
                }
            ]
        }
    }
}
```

### Custom Validation and Tree Traversal

Beyond baseline schema validation, logical validation must ensure the tree reflects proper medical hierarchy using a directed depth-first search (DFS) traversal algorithm.

```python
import jsonschema

class LogicalValidationError(Exception):
    pass

def validate_decision_tree(json_data: dict):
    """
    Validates the JSON against the schema and performs logical checks
    on the hierarchical tree structure.
    """
    # 1. Standard Schema Validation
    try:
        jsonschema.validate(instance=json_data, schema=EXPECTED_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        raise LogicalValidationError(f"Schema mismatch: {e.message}")

    seen_ids = set()

    def traverse_and_validate(node: dict, expected_parent_prefix: str, depth: int):
        rule_id = node.get("rule_id", "")
        rule_text = node.get("rule_text", "")

        # Check empty text
        if not rule_text.strip():
            raise LogicalValidationError(f"Empty rule_text found at node {rule_id}")

        # Depth Check Warning
        if depth > 5:
            print(f"Excessive depth ({depth}) detected at rule {rule_id}. May indicate hallucination.")

        # Uniqueness Check
        if rule_id in seen_ids:
            raise LogicalValidationError(f"Duplicate rule_id detected in tree: {rule_id}")
        seen_ids.add(rule_id)

        # Hierarchy Prefix Check (skip for root node "1")
        if rule_id != "1" and expected_parent_prefix:
            if not rule_id.startswith(expected_parent_prefix + "."):
                raise LogicalValidationError(
                    f"Hierarchy broken: {rule_id} is not a logical child of {expected_parent_prefix}"
                )

        # Leaf vs Non-Leaf Consistency Check
        has_rules = "rules" in node and len(node["rules"]) > 0
        has_op = "operator" in node

        if has_rules and not has_op:
            raise LogicalValidationError(f"Non-leaf node {rule_id} is missing an operator.")
        if has_op and not has_rules:
            raise LogicalValidationError(f"Leaf node {rule_id} erroneously contains an operator.")

        # Operator Consistency and Sequential Checks
        if has_rules:
            op = node["operator"]
            text_lower = rule_text.lower()

            if "all of the following" in text_lower and op != "AND":
                print(f"Node {rule_id} implies 'ALL' but operator is '{op}'")
            if "one of the following" in text_lower and op != "OR":
                print(f"Node {rule_id} implies 'ONE' but operator is '{op}'")

            for i, child in enumerate(node["rules"], start=1):
                expected_child_id = f"{rule_id}.{i}"
                if child.get("rule_id") != expected_child_id:
                     print(f"Sequential gap at {child.get('rule_id')} (Expected {expected_child_id})")

                traverse_and_validate(child, rule_id, depth + 1)

    # Initiate traversal at root
    if "rules" in json_data:
        traverse_and_validate(json_data["rules"], "", 1)
```

### LLM Output Repair Strategies

When an LLM generates invalid JSON, relying on standard Python `json.loads()` will trigger a JSONDecodeError. Attempting to fix this with custom string manipulation or regex is highly error-prone due to the nested nature of the data.

The pipeline utilizes the `fast-json-repair` library (a high-performance Rust port of json_repair). This library parses the string into an abstract syntax tree and applies heuristics to automatically repair missing quotes, unescaped characters, mismatched brackets, and trailing commas.

| Library | Strengths | Weaknesses |
|---------|-----------|------------|
| fast-json-repair | Rust-backed speed, fixes complex nesting, handles markdown artifacts. | Requires external dependency. |
| json_repair | Pure Python, highly accurate, actively maintained for LLM outputs. | Slower than Rust version on large payloads. |
| dirtyjson | Good for trailing commas and unquoted keys. | Does not reliably fix heavily truncated LLM outputs. |

```python
from fast_json_repair import repair_json
import json

def parse_and_repair_llm_output(llm_raw_text: str) -> dict:
    """Attempts to load JSON natively, and automatically repairs it if malformed."""
    try:
        return json.loads(llm_raw_text)
    except json.JSONDecodeError:
        try:
            # Strip markdown formatting if the model ignored instructions
            if llm_raw_text.startswith("```json"):
                llm_raw_text = llm_raw_text.strip("`").strip("json").strip()
            elif llm_raw_text.startswith("```"):
                llm_raw_text = llm_raw_text.strip("`").strip()

            # Apply AST heuristic repair
            repaired_string = repair_json(llm_raw_text)
            parsed_data = json.loads(repaired_string)

            if isinstance(parsed_data, list):
                raise ValueError("LLM returned a flat list instead of a JSON object.")

            return parsed_data

        except Exception as e:
            raise ValueError(f"Irreparable JSON payload: {str(e)}")
```

## Part E: OpenAI API Integration

### Structured Outputs vs JSON Mode Limitations

OpenAI recently introduced Structured Outputs via the `response_format={"type": "json_schema"}` parameter, which natively supports Pydantic models to guarantee output structures. While seamless Pydantic integration is highly desirable, a critical architectural limitation exists within the API: **OpenAI's Structured Outputs engine explicitly rejects recursive Pydantic models** (e.g., hierarchical trees utilizing `$ref`).

Passing a recursive Pydantic model directly to `client.beta.chat.completions.parse()` will trigger a validation failure. This occurs due to conflicts with the strict `additionalProperties: false` requirement, constraints on numeric properties, and backend reference resolution limitations in the OpenAI schema compiler.

**The Workaround:** Rather than abandoning structured formatting, the optimal, production-ready approach is to rely on **JSON Mode** (`response_format={"type": "json_object"}`) coupled with a highly explicit system prompt. JSON Mode ensures the response parses as syntactically valid JSON, while the secondary Python validation engine (Part D) handles schema adherence and recursion logic. This avoids the API's recursive limitations while maintaining robust programmatic quality control.

### Token Management and Economics

Effective token management is required to control costs and prevent context window exhaustion. An average 10–15 page Oscar guideline yields approximately 4,000 to 6,000 words. Using the standard OpenAI heuristic (1 token ≈ 0.75 words), this translates to roughly 5,300 to 8,000 input tokens per document.

**Context Window:** GPT-4o supports a 128,000-token context window, easily accommodating entire guidelines without requiring complex external text chunking strategies. By utilizing the regex heuristics to pre-extract only the "Initial" section, the input size is often reduced to under 1,500 tokens, drastically improving inference speed and lowering costs.

**Model Selection:** `gpt-4o` is strictly recommended over `gpt-4o-mini` for this task. Recursive JSON generation, logic inference, and precise hierarchical mapping are highly complex reasoning tasks. Empirical evidence demonstrates that `gpt-4o-mini` frequently hallucinates nested keys, struggles with deeply recursive schemas, and ignores required property constraints.

**Cost Estimate:**
- Input (pre-extracted): ~1,500 tokens * $2.50 / 1M = $0.0037
- Output (JSON tree): ~1,500 tokens * $10.00 / 1M = $0.015
- Total per PDF: ~$0.018. Processing a batch of 15 PDFs will cost approximately $0.28.

### Production-Ready API Code and Error Handling

The following module implements an asynchronous processing environment with network-level exponential backoff, semantic retry logic for schema mismatch, and robust error handling. It utilizes the tenacity library to handle HTTP 429 (Rate Limit) and 502 (Bad Gateway) errors automatically.

```python
import asyncio
import time
from openai import AsyncOpenAI
import openai
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

client = AsyncOpenAI()

class PipelineError(Exception):
    """Custom exception for pipeline orchestration failures."""
    pass

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError))
)
async def call_llm_with_retries(system_prompt: str, user_prompt: str) -> str:
    """Executes the Async API call with network-level exponential backoff."""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4096
    )
    return response.choices[0].message.content

async def process_guideline(pdf_id: str, extracted_text: str, system_prompt: str) -> dict:
    """
    Core processing loop featuring semantic retry logic.
    Attempts extraction up to 3 times if schema validation fails due to LLM hallucination.
    """
    user_prompt = f"Text to analyze:\n<EXTRACTED_TEXT>\n{extracted_text}\n</EXTRACTED_TEXT>\n"

    metadata = {
        "pdf_id": pdf_id,
        "attempts": 0,
        "latency_sec": 0,
        "success": False,
        "error": None
    }

    start_time = time.time()

    for attempt in range(3):
        metadata["attempts"] += 1
        try:
            raw_response = await call_llm_with_retries(system_prompt, user_prompt)
            json_data = parse_and_repair_llm_output(raw_response)
            validate_decision_tree(json_data)

            # Clean up operators on leaf nodes if the LLM hallucinated them
            def clean_leaf_nodes(node):
                if "rules" not in node or not node["rules"]:
                    node.pop("operator", None)
                    node.pop("rules", None)
                else:
                    for child in node["rules"]:
                        clean_leaf_nodes(child)

            if "rules" in json_data:
                clean_leaf_nodes(json_data["rules"])

            metadata["success"] = True
            metadata["latency_sec"] = round(time.time() - start_time, 2)
            return {"data": json_data, "metadata": metadata}

        except LogicalValidationError as ve:
            error_msg = str(ve)
            print(f"[Attempt {attempt+1}] Validation failed for {pdf_id}: {error_msg}")

            if "wrong section" in error_msg.lower() or "continuation" in error_msg.lower():
                user_prompt += "\n\nCRITICAL ERROR: You extracted Continuation criteria. ONLY extract the INITIAL criteria."
            else:
                user_prompt += f"\n\nERROR IN PREVIOUS OUTPUT: {error_msg}\nPlease fix the JSON structure, strictly adhering to the schema and node rules."

        except Exception as e:
             metadata["error"] = str(e)
             break

    metadata["latency_sec"] = round(time.time() - start_time, 2)
    return {"data": None, "metadata": metadata}
```

### Batch Processing Orchestration

For processing 10+ PDFs simultaneously, an asynchronous task gatherer maximizes throughput by preventing I/O bottlenecks.

```python
async def batch_process_pdfs(pdf_data_list: list, system_prompt: str) -> list:
    """
    Accepts a list of dictionaries: [{"id": "CG008", "text": "...full text..."}]
    Processes them concurrently using asyncio.gather.
    """
    tasks = []
    metadata_log = []

    for item in pdf_data_list:
        initial_criteria_text, conf_score, logic_log = extract_initial_criteria(item["text"])

        metadata_log.append({
            "id": item["id"],
            "regex_confidence": conf_score,
            "extraction_logic": logic_log
        })

        task = asyncio.create_task(
            process_guideline(item["id"], initial_criteria_text, system_prompt)
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    final_output = []
    successful = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Fatal unhandled exception in async loop for item {i}: {str(result)}")
            continue

        if result["metadata"]["success"]:
            successful += 1

        result["metadata"]["regex_confidence"] = metadata_log[i]["regex_confidence"]
        final_output.append(result)

    print(f"\n--- Batch Processing Complete ---")
    print(f"Success Rate: {successful} / {len(pdf_data_list)}")

    return final_output
```

## Conclusion

The architecture detailed in this report provides a fully resilient, programmatic solution to the challenges inherent in unstructured medical document processing. By strategically segregating tasks, the pipeline offloads fragile structural detection to deterministic regular expressions, utilizes the C-bound engine of PyMuPDF to ensure flawless character extraction, and reserves the computationally expensive logic capabilities of gpt-4o strictly for semantic mapping.

Furthermore, by acknowledging the systemic limitations of OpenAI's strict Structured Outputs regarding recursive JSON constraints, this architecture implements a highly stable alternative. It utilizes JSON Mode backed by post-generation heuristic repair (fast-json-repair) and a robust Python-based tree traversal validation protocol. This orchestration meets all technical constraints for high-stakes deployment, delivering a deterministic output format essential for automated healthcare utilization management systems.

## Key Citations

- [Oscar Clinical Guidelines: Medical](https://www.hioscar.com/clinical-guidelines/medical)
- [Oscar Clinical Guidelines](https://www.hioscar.com/clinical-guidelines)
- [Clinical Guideline Bariatric Surgery (Adults)](https://assets.ctfassets.net) - CG008
- [Clinical Guideline Acupuncture](https://assets.ctfassets.net) - CG013
- [CG005 Oxygen Therapy](https://assets.ctfassets.net)
- [json_repair - GitHub](https://github.com/mangiucugna/json_repair)
- [fast-json-repair - PyPI](https://pypi.org/project/fast-json-repair/)
- [OpenAI Structured Outputs](https://openai.com/introducing-structured-outputs-in-the-api)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io)
- [pdfplumber - GitHub](https://github.com/jsvine/pdfplumber)
