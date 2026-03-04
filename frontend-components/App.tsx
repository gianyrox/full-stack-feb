import React, { useEffect, useState } from "react";
import type { Policy, StructuredPolicy } from "./types";
import PolicyList from "./PolicyList";
import PolicyDetail from "./PolicyDetail";

const MOCK_STRUCTURED: StructuredPolicy = {
  title: "Medical Necessity Criteria for Bariatric Surgery",
  insurance_name: "Oscar Health",
  rules: {
    rule_id: "1",
    rule_text:
      "Procedures are considered medically necessary when ALL of the following criteria are met",
    operator: "AND",
    rules: [
      {
        rule_id: "1.1",
        rule_text:
          "Informed consent with appropriate explanation of risks, benefits, and alternatives",
      },
      {
        rule_id: "1.2",
        rule_text: "Adult aged 18 years or older with documentation of",
        operator: "OR",
        rules: [
          { rule_id: "1.2.1", rule_text: "Body mass index (BMI) \u226540" },
          {
            rule_id: "1.2.2",
            rule_text:
              "BMI \u226535 with ONE of the following severe obesity-related comorbidities",
            operator: "OR",
            rules: [
              {
                rule_id: "1.2.2.1",
                rule_text:
                  "Clinically significant cardio-pulmonary disease (e.g. severe OSA, OHS)",
              },
              {
                rule_id: "1.2.2.2",
                rule_text: "Coronary artery disease, objectively documented",
              },
              {
                rule_id: "1.2.2.3",
                rule_text: "Objectively documented cardiomyopathy",
              },
              {
                rule_id: "1.2.2.4",
                rule_text:
                  "Medically refractory hypertension (>140/90 despite 3 agents)",
              },
              {
                rule_id: "1.2.2.5",
                rule_text: "Type 2 diabetes mellitus",
              },
              {
                rule_id: "1.2.2.6",
                rule_text:
                  "Nonalcoholic fatty liver disease or nonalcoholic steatohepatitis",
              },
              {
                rule_id: "1.2.2.7",
                rule_text: "Osteoarthritis of the knee or hip",
              },
              {
                rule_id: "1.2.2.8",
                rule_text: "Urinary stress incontinence",
              },
            ],
          },
          {
            rule_id: "1.2.3",
            rule_text: "BMI \u226530-34.9, see section below",
          },
        ],
      },
      {
        rule_id: "1.3",
        rule_text:
          "Failure to achieve and maintain successful long-term weight loss via non-surgical therapy",
      },
      {
        rule_id: "1.4",
        rule_text:
          "The proposed bariatric surgery includes a comprehensive pre- and post-operative plan",
        operator: "AND",
        rules: [
          {
            rule_id: "1.4.1",
            rule_text:
              "Preoperative evaluation to rule out and treat any other reversible causes of weight gain/obesity",
            operator: "AND",
            rules: [
              {
                rule_id: "1.4.1.1",
                rule_text:
                  "Basic laboratory testing (blood glucose, lipid panel, CBC, metabolic panel, etc.)",
              },
              {
                rule_id: "1.4.1.2",
                rule_text:
                  "Nutrient deficiency screening and formal nutrition evaluation",
              },
              {
                rule_id: "1.4.1.3",
                rule_text: "Cardiopulmonary risk evaluation",
              },
              { rule_id: "1.4.1.4", rule_text: "GI evaluation" },
              { rule_id: "1.4.1.5", rule_text: "Endocrine evaluation" },
              {
                rule_id: "1.4.1.6",
                rule_text:
                  "Age appropriate cancer screening verified complete and up to date",
              },
              {
                rule_id: "1.4.1.7",
                rule_text: "Smoking cessation counseling, if applicable",
              },
            ],
          },
        ],
      },
      {
        rule_id: "1.5",
        rule_text: "Psycho-social behavioral evaluation",
        operator: "AND",
        rules: [
          {
            rule_id: "1.5.1",
            rule_text: "No current substance abuse has been identified",
          },
          {
            rule_id: "1.5.2",
            rule_text:
              "Members with the following conditions MUST have formal preoperative psychological clearance",
            operator: "OR",
            rules: [
              {
                rule_id: "1.5.2.1",
                rule_text:
                  "History of schizophrenia, borderline personality disorder, suicidal ideation, severe depression",
              },
              {
                rule_id: "1.5.2.2",
                rule_text:
                  "Currently under care of a psychologist/psychiatrist",
              },
              {
                rule_id: "1.5.2.3",
                rule_text: "On psychotropic medications",
              },
            ],
          },
        ],
      },
    ],
  },
};

const MOCK_POLICIES: Policy[] = [
  {
    id: 1,
    title: "Medical Necessity Criteria for Bariatric Surgery",
    pdf_url: "https://www.hioscar.com/docs/bariatric-surgery.pdf",
    source_page_url: "https://www.hioscar.com/clinical-guidelines/medical",
    discovered_at: "2025-01-15T10:30:00Z",
    has_structured: true,
  },
  {
    id: 2,
    title: "Cardiac Rehabilitation Services",
    pdf_url: "https://www.hioscar.com/docs/cardiac-rehab.pdf",
    source_page_url: "https://www.hioscar.com/clinical-guidelines/medical",
    discovered_at: "2025-01-15T10:31:00Z",
    has_structured: true,
  },
  {
    id: 3,
    title: "Durable Medical Equipment (DME)",
    pdf_url: "https://www.hioscar.com/docs/dme.pdf",
    source_page_url: "https://www.hioscar.com/clinical-guidelines/medical",
    discovered_at: "2025-01-15T10:32:00Z",
    has_structured: false,
  },
  {
    id: 4,
    title: "Gender Affirming Care",
    pdf_url: "https://www.hioscar.com/docs/gender-affirming.pdf",
    source_page_url: "https://www.hioscar.com/clinical-guidelines/medical",
    discovered_at: "2025-01-15T10:33:00Z",
    has_structured: true,
  },
  {
    id: 5,
    title: "Physical and Occupational Therapy",
    pdf_url: "https://www.hioscar.com/docs/pt-ot.pdf",
    source_page_url: "https://www.hioscar.com/clinical-guidelines/medical",
    discovered_at: "2025-01-15T10:34:00Z",
    has_structured: false,
  },
];

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [policies, setPolicies] = useState<Policy[]>(MOCK_POLICIES);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [structuredData, setStructuredData] =
    useState<StructuredPolicy | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/policies`)
      .then((res) => res.json())
      .then((data: Policy[]) => setPolicies(data))
      .catch(() => {
        console.warn("API unavailable, using mock data");
      });
  }, []);

  const handleSelect = async (policyId: number) => {
    setSelectedId(policyId);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/policies/${policyId}/structured`);
      if (res.ok) {
        const data: StructuredPolicy = await res.json();
        setStructuredData(data);
      } else {
        throw new Error("not found");
      }
    } catch {
      // Fallback to mock for policy id 1
      if (policyId === 1) {
        setStructuredData(MOCK_STRUCTURED);
      } else {
        setStructuredData(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const selectedPolicy = policies.find((p) => p.id === selectedId) ?? null;

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-900">
          Oscar Medical Guidelines
        </h1>
        <p className="text-sm text-slate-500">
          Browse policies and structured criteria trees
        </p>
      </header>

      <div className="flex gap-6 p-6 max-w-7xl mx-auto">
        <aside className="w-96 flex-shrink-0">
          <PolicyList
            policies={policies}
            onSelect={handleSelect}
            selectedId={selectedId ?? undefined}
          />
        </aside>

        <main className="flex-1 min-w-0">
          {loading ? (
            <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-slate-400">
              Loading...
            </div>
          ) : selectedPolicy ? (
            <PolicyDetail
              policy={selectedPolicy}
              structuredData={structuredData}
            />
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-slate-400">
              Select a policy from the list to view details.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
