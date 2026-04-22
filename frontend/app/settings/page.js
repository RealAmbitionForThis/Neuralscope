import BackendConnection from "@/components/settings/BackendConnection";
import TokenManager from "@/components/settings/TokenManager";
import RunPodPanel from "@/components/runpod/RunPodPanel";

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted mt-1">
          Backend connection, access tokens, and RunPod pod management.
        </p>
      </div>
      <BackendConnection />
      <TokenManager />
      <RunPodPanel />
    </div>
  );
}
