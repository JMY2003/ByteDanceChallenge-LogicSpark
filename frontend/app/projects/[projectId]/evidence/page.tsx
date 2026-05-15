import { ListChecks } from "lucide-react";
import { EvidenceList } from "@/components/evidence/EvidenceList";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getEvidence } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function EvidencePage({ params }: PageProps) {
  const { projectId } = await params;
  const evidence = await getEvidence(projectId);
  return (
    <main className="min-h-screen px-6 py-6">
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-signal">
              <ListChecks size={16} />
              Evidence
            </div>
            <h1 className="mt-2 text-3xl font-semibold text-ink">证据列表</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
        <EvidenceList projectId={projectId} evidence={evidence} />
      </div>
    </main>
  );
}

