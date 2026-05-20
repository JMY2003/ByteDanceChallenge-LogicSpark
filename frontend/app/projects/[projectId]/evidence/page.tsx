import { ListChecks } from "lucide-react";
import { EvidenceList } from "@/components/evidence/EvidenceList";
import { MiraBrand } from "@/components/ui/MiraBrand";
import { ProjectNav } from "@/components/ui/ProjectNav";
import { getEvidence } from "@/lib/api";

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function EvidencePage({ params }: PageProps) {
  const { projectId } = await params;
  const evidence = await getEvidence(projectId);
  return (
    <main className="app-page">
      <div className="shell-wide mb-5">
        <MiraBrand />
      </div>
      <div className="shell-wide mb-5">
        <header className="project-header-card flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-signal">
              <ListChecks size={16} />
              Evidence
            </div>
            <h1 className="mt-2 page-title">证据列表</h1>
          </div>
          <ProjectNav projectId={projectId} />
        </header>
      </div>
      <div className="shell-wide space-y-5">
        <EvidenceList projectId={projectId} evidence={evidence} />
      </div>
    </main>
  );
}
