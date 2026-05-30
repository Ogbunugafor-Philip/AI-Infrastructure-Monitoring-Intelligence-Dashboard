"use client";

import { BrainCircuit } from "lucide-react";
import { withAuth } from "@/lib/withAuth";
import { EmptyState } from "@/components/EmptyState";

function AiReportsPage() {
  return (
    <div className="space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <BrainCircuit className="h-6 w-6 text-indigo-400" /> AI Reports
      </h1>
      <EmptyState
        title="No AI reports yet"
        description="AI-generated infrastructure risk reports and recommendations will appear here once generated."
        icon={<BrainCircuit className="h-6 w-6" />}
      />
    </div>
  );
}

export default withAuth(AiReportsPage, ["viewer", "admin", "super_admin"]);
