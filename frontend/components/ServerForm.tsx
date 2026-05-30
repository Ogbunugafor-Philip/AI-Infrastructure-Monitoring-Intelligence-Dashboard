"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, Lock, PlugZap, Save } from "lucide-react";
import {
  type Server,
  type ServerCreatePayload,
  type TestConnectionPayload,
  errorMessage,
  registerServer,
  testConnection,
  updateServer,
  verifyPassword,
} from "@/lib/api";
import { type ServerFormValues, validateServerForm } from "@/lib/validation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Alert } from "@/components/ui/alert";
import { PasswordPromptDialog } from "@/components/PasswordPromptDialog";

interface Props {
  mode: "create" | "edit";
  server?: Server;
}

function initialValues(server?: Server): ServerFormValues {
  return {
    name: server?.name ?? "",
    ip_address: server?.ip_address ?? "",
    ssh_port: server?.ssh_port ?? 22,
    ssh_username: server?.ssh_username ?? "",
    ssh_auth_method: server?.ssh_auth_method ?? "password",
    ssh_password: "",
    ssh_key: "",
    ssh_key_only_mode: server?.ssh_key_only_mode ?? false,
    allowed_ip_whitelist: server?.allowed_ip_whitelist ?? "",
  };
}

export function ServerForm({ mode, server }: Props) {
  const router = useRouter();
  const [values, setValues] = useState<ServerFormValues>(() => initialValues(server));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [keyRevealed, setKeyRevealed] = useState(false);
  const [pwModalOpen, setPwModalOpen] = useState(false);

  // In edit mode, leaving credential fields blank keeps the stored value.
  const requireCredential = mode === "create";

  function update<K extends keyof ServerFormValues>(field: K, value: ServerFormValues[K]) {
    setValues((prev) => ({ ...prev, [field]: value }));
    // Any change to connection-relevant data invalidates a prior test result.
    setTestResult(null);
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field as string];
      return next;
    });
  }

  const credentialEnteredOrEditingExisting = useMemo(() => {
    if (mode === "create") return true;
    const hasNew = values.ssh_password.trim() || values.ssh_key.trim();
    return Boolean(hasNew) || Boolean(server);
  }, [mode, values.ssh_password, values.ssh_key, server]);

  function runValidation(): boolean {
    const errs = validateServerForm(values, { requireCredential });
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleTest() {
    setSaveError(null);
    if (!runValidation()) return;
    setTesting(true);
    setTestResult(null);
    try {
      // Edit + no new credential typed -> test the stored server by id.
      const useStored =
        mode === "edit" && !values.ssh_password.trim() && !values.ssh_key.trim();
      const payload: TestConnectionPayload = useStored
        ? { server_id: server!.id }
        : {
            ip_address: values.ip_address,
            ssh_port: Number(values.ssh_port),
            ssh_username: values.ssh_username,
            ssh_auth_method: values.ssh_auth_method,
            ssh_password:
              values.ssh_auth_method === "password" ? values.ssh_password : null,
            ssh_key: values.ssh_auth_method === "key" ? values.ssh_key : null,
            ssh_key_only_mode: values.ssh_key_only_mode,
          };
      const result = await testConnection(payload);
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: errorMessage(err, "Connection test failed.") });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    setSaveError(null);
    if (!runValidation()) return;
    setSaving(true);
    try {
      if (mode === "create") {
        const payload: ServerCreatePayload = {
          name: values.name.trim(),
          ip_address: values.ip_address.trim(),
          ssh_port: Number(values.ssh_port),
          ssh_username: values.ssh_username.trim(),
          ssh_auth_method: values.ssh_auth_method,
          ssh_password: values.ssh_auth_method === "password" ? values.ssh_password : null,
          ssh_key: values.ssh_auth_method === "key" ? values.ssh_key : null,
          ssh_key_only_mode: values.ssh_key_only_mode,
          allowed_ip_whitelist: values.allowed_ip_whitelist.trim() || null,
        };
        await registerServer(payload);
      } else {
        const payload: Partial<ServerCreatePayload> = {
          name: values.name.trim(),
          ip_address: values.ip_address.trim(),
          ssh_port: Number(values.ssh_port),
          ssh_username: values.ssh_username.trim(),
          ssh_auth_method: values.ssh_auth_method,
          ssh_key_only_mode: values.ssh_key_only_mode,
          allowed_ip_whitelist: values.allowed_ip_whitelist.trim() || null,
        };
        if (values.ssh_password.trim()) payload.ssh_password = values.ssh_password;
        if (values.ssh_key.trim()) payload.ssh_key = values.ssh_key;
        await updateServer(server!.id, payload);
      }
      router.push("/servers");
    } catch (err) {
      setSaveError(errorMessage(err, "Failed to save server."));
    } finally {
      setSaving(false);
    }
  }

  const saveDisabled =
    saving || (mode === "create" && !testResult?.success);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label htmlFor="name">Server Name</Label>
          <Input
            id="name"
            value={values.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="prod-web-01"
          />
          {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name}</p>}
        </div>

        <div>
          <Label htmlFor="ip">Server IP Address</Label>
          <Input
            id="ip"
            value={values.ip_address}
            onChange={(e) => update("ip_address", e.target.value)}
            placeholder="10.0.0.5"
          />
          {errors.ip_address && (
            <p className="mt-1 text-xs text-red-400">{errors.ip_address}</p>
          )}
        </div>

        <div>
          <Label htmlFor="port">SSH Port</Label>
          <Input
            id="port"
            type="number"
            min={1}
            max={65535}
            value={values.ssh_port}
            onChange={(e) => update("ssh_port", Number(e.target.value))}
          />
          {errors.ssh_port && <p className="mt-1 text-xs text-red-400">{errors.ssh_port}</p>}
        </div>

        <div>
          <Label htmlFor="username">SSH Username</Label>
          <Input
            id="username"
            value={values.ssh_username}
            onChange={(e) => update("ssh_username", e.target.value)}
            placeholder="ubuntu"
          />
          {errors.ssh_username && (
            <p className="mt-1 text-xs text-red-400">{errors.ssh_username}</p>
          )}
        </div>

        <div>
          <Label>Authentication Method</Label>
          <div className="inline-flex rounded-lg border border-slate-700 p-1">
            <button
              type="button"
              onClick={() => update("ssh_auth_method", "password")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${
                values.ssh_auth_method === "password"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300"
              }`}
            >
              <Lock className="h-3.5 w-3.5" /> Password
            </button>
            <button
              type="button"
              onClick={() => update("ssh_auth_method", "key")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${
                values.ssh_auth_method === "key"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300"
              }`}
            >
              <KeyRound className="h-3.5 w-3.5" /> SSH Key
            </button>
          </div>
        </div>
      </div>

      {/* Conditional credential fields */}
      {values.ssh_auth_method === "password" ? (
        <div>
          <Label htmlFor="password">
            SSH Password {mode === "edit" && <span className="text-slate-500">(leave blank to keep)</span>}
          </Label>
          <Input
            id="password"
            type="password"
            value={values.ssh_password}
            onChange={(e) => update("ssh_password", e.target.value)}
            placeholder="••••••••"
            autoComplete="new-password"
          />
          {errors.ssh_password && (
            <p className="mt-1 text-xs text-red-400">{errors.ssh_password}</p>
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between">
            <Label htmlFor="key">
              SSH Private Key {mode === "edit" && <span className="text-slate-500">(leave blank to keep)</span>}
            </Label>
            <button
              type="button"
              onClick={() => {
                if (keyRevealed) setKeyRevealed(false);
                else setPwModalOpen(true);
              }}
              className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
            >
              {keyRevealed ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              {keyRevealed ? "Hide" : "Show"}
            </button>
          </div>
          <Textarea
            id="key"
            value={values.ssh_key}
            onChange={(e) => update("ssh_key", e.target.value)}
            placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
            style={
              keyRevealed
                ? undefined
                : ({ WebkitTextSecurity: "disc" } as React.CSSProperties)
            }
          />
          {errors.ssh_key && <p className="mt-1 text-xs text-red-400">{errors.ssh_key}</p>}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex items-center justify-between rounded-lg border border-slate-800 px-4 py-3">
          <div>
            <Label className="mb-0">SSH Key Only Mode</Label>
            <p className="text-xs text-slate-500">Reject password auth for this server.</p>
          </div>
          <Switch
            checked={values.ssh_key_only_mode}
            onCheckedChange={(c) => update("ssh_key_only_mode", c)}
          />
        </div>
        <div>
          <Label htmlFor="whitelist">Allowed IP Whitelist</Label>
          <Input
            id="whitelist"
            value={values.allowed_ip_whitelist}
            onChange={(e) => update("allowed_ip_whitelist", e.target.value)}
            placeholder="127.0.0.1, 10.0.0.0/24"
          />
          {errors.allowed_ip_whitelist && (
            <p className="mt-1 text-xs text-red-400">{errors.allowed_ip_whitelist}</p>
          )}
        </div>
      </div>
      {errors.ssh_key_only_mode && (
        <p className="text-xs text-red-400">{errors.ssh_key_only_mode}</p>
      )}

      {/* Test result banner */}
      {testResult && (
        <Alert variant={testResult.success ? "success" : "destructive"}>
          {testResult.success ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <PlugZap className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{testResult.message}</span>
        </Alert>
      )}
      {saveError && <Alert variant="destructive">{saveError}</Alert>}

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={handleTest}
          disabled={testing || !credentialEnteredOrEditingExisting}
        >
          {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlugZap className="h-4 w-4" />}
          Test Connection
        </Button>
        <Button type="button" onClick={handleSave} disabled={saveDisabled}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {mode === "create" ? "Save Server" : "Update Server"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => router.push("/servers")}>
          Cancel
        </Button>
        {mode === "create" && !testResult?.success && (
          <span className="text-xs text-slate-500">
            Run a successful connection test to enable saving.
          </span>
        )}
      </div>

      {/* Reveal-key password gate */}
      <PasswordPromptDialog
        open={pwModalOpen}
        onOpenChange={setPwModalOpen}
        title="Reveal SSH key"
        description="Re-enter your dashboard password to display the private key."
        onConfirm={async (pw) => ((await verifyPassword(pw)) ? true : "Password verification failed.")}
        onSuccess={() => setKeyRevealed(true)}
      />
    </div>
  );
}
