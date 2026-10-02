export interface SSEMessage {
  event: string;
  data: string;
}

export function createSSEParser(onMessage: (m: SSEMessage) => void) {
  let buffer = "";
  return {
    push(chunk: string) {
      buffer = (buffer + chunk).replace(/\r\n/g, "\n");
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        let event = "message";
        const data: string[] = [];
        for (const line of raw.split("\n")) {
          if (line.startsWith(":")) continue;
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        if (data.length) onMessage({ event, data: data.join("\n") });
      }
    },
  };
}

export async function readSSE(body: ReadableStream<Uint8Array>, onMessage: (m: SSEMessage) => void): Promise<void> {
  const parser = createSSEParser(onMessage);
  const reader = body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parser.push(decoder.decode(value, { stream: true }));
  }
  parser.push(decoder.decode() + "\n\n");
}
