"use client";

import { UnreviewedBadge } from "@/components/UnreviewedBadge";
import { api } from "@/lib/api";
import type { ExercisePublic, SessionSummary } from "@/lib/types";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Home() {
  const router = useRouter();
  const [exercises, setExercises] = useState<ExercisePublic[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listExercises().then(setExercises).catch((e) => setError(e.message));
    api.listSessions().then(setSessions).catch(() => setSessions([]));
  }, []);

  async function start(exerciseId: string) {
    setBusy(exerciseId);
    try {
      const { id } = await api.createSession({ exercise_id: exerciseId });
      router.push(`/sessoes/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  return (
    <div className="space-y-10">
      <section className="max-w-3xl space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">Interprete espectros de RMN de ¹H com um tutor</h1>
        <p className="text-muted">
          Observe, levante hipóteses e confronte-as com os dados. O tutor faz perguntas, dá pistas graduais e usa
          ferramentas determinísticas para os valores numéricos — você continua no centro do raciocínio.
        </p>
        <Link
          href="/sessoes/nova"
          className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Enviar meu espectro
        </Link>
      </section>

      {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad">{error}</p>}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Exercícios</h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {exercises.map((ex) => (
            <li key={ex.id} data-testid={`exercise-${ex.id}`} className="flex flex-col gap-2 rounded-lg border border-line bg-card p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{ex.title}</h3>
                {!ex.reviewed && <UnreviewedBadge />}
              </div>
              <p className="font-mono text-xs text-muted">
                {ex.metadata.frequency_mhz} MHz · {ex.metadata.solvent} · dificuldade {ex.difficulty}
              </p>
              <button
                onClick={() => start(ex.id)}
                disabled={busy !== null}
                className="mt-auto self-start rounded-md border border-accent px-3 py-1.5 text-sm text-accent hover:bg-accent-soft disabled:opacity-50"
              >
                {busy === ex.id ? "Abrindo…" : "Começar"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {sessions.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Minhas sessões</h2>
          <ul className="divide-y divide-line rounded-lg border border-line bg-card">
            {sessions.map((s) => (
              <li key={s.id}>
                <Link href={`/sessoes/${s.id}`} className="flex justify-between px-4 py-2 text-sm hover:bg-paper">
                  <span>{s.title}</span>
                  <span className="font-mono text-xs text-muted">{new Date(s.updated_at).toLocaleString("pt-BR")}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
