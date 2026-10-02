declare module "plotly.js-dist-min" {
  type PlotlyEvent = Record<string, unknown> & { points?: { x: number }[] };
  export interface PlotlyHTMLElement extends HTMLDivElement {
    on(event: string, handler: (ev: PlotlyEvent) => void): void;
    removeAllListeners?(event: string): void;
  }
  const Plotly: {
    react(el: HTMLElement, data: object[], layout?: object, config?: object): Promise<PlotlyHTMLElement>;
    purge(el: HTMLElement): void;
  };
  export default Plotly;
}
