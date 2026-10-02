export const TOOL_LABELS: Record<string, string> = {
  get_spectrum_metadata: "consultou os metadados",
  get_peak_list: "consultou a lista de picos",
  get_peaks_in_region: "consultou uma região do espectro",
  get_peak: "consultou um pico",
  get_integration: "consultou integrais",
  calculate_delta: "calculou Δδ",
  calculate_j: "consultou constantes J",
  validate_smiles: "validou um SMILES",
  molecular_formula: "calculou a fórmula",
  degrees_of_unsaturation: "calculou o IDH",
  compare_structure_with_data: "checou a estrutura contra os dados",
  update_session_state: "atualizou o quadro de hipóteses",
  check_against_answer: "comparou com a resposta do exercício",
};

export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? name;
}
