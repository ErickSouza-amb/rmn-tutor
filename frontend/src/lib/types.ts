export type Multiplicity = "s" | "d" | "t" | "q" | "quint" | "sext" | "sept" | "m" | "dd" | "dt" | "td" | "ddd" | "br_s";
export const MULTIPLICITIES: Multiplicity[] = ["s", "d", "t", "q", "quint", "sext", "sept", "m", "dd", "dt", "td", "ddd", "br_s"];

export type AssistMode = "tutor" | "hint" | "verify" | "solution";
export const MODE_LABELS: Record<AssistMode, string> = {
  tutor: "Tutor",
  hint: "Dica",
  verify: "Verificação",
  solution: "Solução completa",
};

export interface Peak {
  id: string;
  ppm: number;
  integral: number | null;
  multiplicity: Multiplicity | null;
  j_hz: number[] | null;
  source: "user" | "exercise" | "engine";
  note: string | null;
}

export interface SessionMetadata {
  frequency_mhz?: number | null;
  solvent?: string | null;
  molecular_formula?: string | null;
  notes?: string | null;
}

export interface ExercisePublic {
  id: string;
  title: string;
  difficulty: number;
  experiment: string;
  metadata: SessionMetadata;
  reviewed: boolean;
  notes: string | null;
}

export interface ChatMessage {
  seq: number;
  role: "user" | "assistant";
  text: string;
  mode: string | null;
  created_at: string;
}

export interface ChemState {
  schema_version: 1;
  stage: string;
  signal_notes: { peak_id: string; interpretation: string; status: string }[];
  hypotheses: { id: string; text: string; by: string; status: string; evidence: string[] }[];
  unresolved: string[];
  hints_given: number;
  proposed_structures: { smiles: string; check_id: string | null }[];
}

export interface SessionData {
  id: string;
  title: string;
  experiment: string;
  metadata: SessionMetadata;
  exercise: { id: string; title: string; reviewed: boolean; notes: string | null } | null;
  has_image: boolean;
  peaks: Peak[];
  chem_state: ChemState;
  assist_mode: AssistMode;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface SessionSummary {
  id: string;
  title: string;
  exercise_id: string | null;
  updated_at: string;
}

export interface ParseResult {
  peaks: Peak[];
  errors: { line: number; message: string }[];
}

export interface Spectrum {
  x: number[];
  y: number[];
  warnings: string[];
}

export interface StructureCheck {
  canonical_smiles: string;
  formula: string;
  total_h: number;
  h_environments: { count: number; h_class: string; label: string; expected_range_ppm: [number, number] }[];
  checks: { name: string; status: "pass" | "fail" | "inconclusive"; detail: string; heuristic: boolean }[];
  limitations: string[];
  matches_answer?: boolean;
  check_id: string;
}

export type TurnEvent =
  | { event: "text_delta"; data: { text: string } }
  | { event: "tool_call"; data: { name: string; input: unknown } }
  | { event: "tool_result"; data: { name: string; ok: boolean } }
  | { event: "state_updated"; data: { chem_state: ChemState } }
  | { event: "done"; data: { text: string; chem_state: ChemState; assist_mode: AssistMode } }
  | { event: "error"; data: { code: string; message: string } };
