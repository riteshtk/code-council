"use client";

import { useState, useEffect } from "react";
import { useConfigStore } from "@/stores/configStore";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Settings,
  Cpu,
  Users,
  FolderOpen,
  FileOutput,
  Save,
  ChevronDown,
  ChevronUp,
  Check,
  Eye,
  Shield,
  Brain,
  PenTool,
  Zap,
  Globe,
  Server,
  MonitorSpeaker,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

/* ─── Agent metadata ─── */
const AGENTS_META: Record<string, { label: string; role: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  archaeologist: { label: "The Archaeologist", role: "Historian", color: "#d4a574", icon: Eye },
  skeptic:       { label: "The Skeptic",       role: "Challenger", color: "#ff6b6b", icon: Shield },
  visionary:     { label: "The Visionary",     role: "Proposer", color: "#6c5ce7", icon: Brain },
  scribe:        { label: "The Scribe",        role: "Secretary", color: "#4ecdc4", icon: PenTool },
};

const PROVIDER_META: Record<string, { icon: React.ComponentType<{ className?: string }>; placeholder: string }> = {
  openai:    { icon: Zap,            placeholder: "sk-..." },
  anthropic: { icon: Brain,          placeholder: "sk-ant-..." },
  gemini:    { icon: Globe,          placeholder: "AIza..." },
  mistral:   { icon: Server,         placeholder: "..." },
  ollama:    { icon: MonitorSpeaker, placeholder: "N/A (local)" },
};

/* ─── Section header ─── */
function SectionHeader({ title, description, icon: Icon }: {
  title: string;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2.5 mb-1">
        <div className="w-7 h-7 rounded-lg bg-[var(--cc-accent-muted)] flex items-center justify-center">
          <Icon className="w-4 h-4 text-[var(--cc-accent)]" />
        </div>
        <h2 className="text-base font-semibold text-[var(--cc-text)] tracking-tight">{title}</h2>
      </div>
      {description && (
        <p className="text-sm text-[var(--cc-text-muted)] ml-[38px]">{description}</p>
      )}
    </div>
  );
}

/* ─── Agent card ─── */
function AgentCard({ handle, agentCfg, onUpdate }: {
  handle: string;
  agentCfg: Record<string, unknown>;
  onUpdate: (patch: Record<string, unknown>) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = AGENTS_META[handle] || { label: handle, role: handle, color: "var(--cc-accent)", icon: Zap };
  const Icon = meta.icon;
  const enabled = agentCfg?.enabled !== false;
  const provider = (agentCfg?.provider as string) || "default";
  const model = (agentCfg?.model as string) || "";
  const temperature = (agentCfg?.temperature as number) ?? 0.3;

  return (
    <div className={cn(
      "rounded-xl overflow-hidden transition-all duration-300",
      "border bg-[var(--cc-bg-elevated)]",
      enabled ? "border-[var(--cc-border-hover)]" : "border-[var(--cc-border)] opacity-60"
    )}>
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3.5 cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-200"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Agent avatar */}
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${meta.color}18` }}
        >
          <span style={{ color: meta.color }}><Icon className="w-4 h-4" /></span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[var(--cc-text)]">{meta.label}</span>
            <span
              className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
              style={{ color: meta.color, backgroundColor: `${meta.color}15` }}
            >
              {meta.role}
            </span>
          </div>
          <div className="text-xs text-[var(--cc-text-muted)] mt-0.5">
            {provider}{model ? ` · ${model}` : ""} · temp {temperature}
          </div>
        </div>

        {/* Toggle + expand */}
        <div className="flex items-center gap-3">
          <button
            onClick={(e) => { e.stopPropagation(); onUpdate({ enabled: !enabled }); }}
            className="relative inline-flex h-5 w-9 items-center rounded-full cursor-pointer transition-colors duration-200"
            style={{ backgroundColor: enabled ? meta.color : "var(--cc-bg-active)" }}
          >
            <span className={cn(
              "inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform duration-200",
              enabled ? "translate-x-4" : "translate-x-0.5"
            )} />
          </button>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-[var(--cc-text-muted)]" />
            : <ChevronDown className="w-4 h-4 text-[var(--cc-text-muted)]" />
          }
        </div>
      </div>

      {/* Expanded settings */}
      {expanded && (
        <div className="px-4 pb-4 pt-3 space-y-4 border-t border-[var(--cc-border)] animate-fade-in bg-[var(--cc-bg)]">
          <div className="grid grid-cols-3 gap-3">
            <FieldGroup label="Provider">
              <Input
                value={provider === "default" ? "" : provider}
                onChange={(e) => onUpdate({ provider: e.target.value || "" })}
                placeholder="(inherit default)"
                className="h-8 text-xs rounded-lg"
              />
            </FieldGroup>
            <FieldGroup label="Model">
              <Input
                value={model}
                onChange={(e) => onUpdate({ model: e.target.value })}
                placeholder="(provider default)"
                className="h-8 text-xs rounded-lg"
              />
            </FieldGroup>
            <FieldGroup label="Temperature">
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={temperature * 100}
                  onChange={(e) => onUpdate({ temperature: Number(e.target.value) / 100 })}
                  className="flex-1 accent-[var(--cc-accent)] cursor-pointer h-1.5"
                />
                <span className="text-xs font-mono text-[var(--cc-accent)] w-8 text-right">{temperature.toFixed(1)}</span>
              </div>
            </FieldGroup>
          </div>
        </div>
      )}
    </div>
  );
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-semibold text-[var(--cc-text-muted)] uppercase tracking-wider">{label}</label>
      {children}
    </div>
  );
}

/* ─── Toggle switch ─── */
function Toggle({ enabled, onChange, label }: { enabled: boolean; onChange: () => void; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onChange}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full cursor-pointer transition-colors duration-200",
          enabled ? "bg-[var(--cc-accent)]" : "bg-[var(--cc-bg-active)]"
        )}
      >
        <span className={cn(
          "inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200",
          enabled ? "translate-x-6" : "translate-x-1"
        )} />
      </button>
      <span className="text-sm text-[var(--cc-text-secondary)]">
        {enabled ? "Enabled" : "Disabled"}
      </span>
    </div>
  );
}

/* ─── Main page ─── */
export default function ConfigPage() {
  const { config, loading, loadConfig, updateConfig } = useConfigStore();
  const [dirty, setDirty] = useState(false);
  const [localConfig, setLocalConfig] = useState(config);
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadConfig(); }, []);
  useEffect(() => { setLocalConfig(config); }, [config]);

  const lc = (localConfig ?? {}) as Record<string, unknown>;
  const council = (lc.council ?? {}) as Record<string, unknown>;
  const llm = (lc.llm ?? {}) as Record<string, unknown>;
  const providers = ((llm.providers ?? lc.providers ?? {}) as Record<string, Record<string, unknown>>);
  const agents = (lc.agents ?? {}) as Record<string, unknown>;
  const ingest = (lc.ingest ?? lc.ingestion ?? {}) as Record<string, unknown>;

  function patch(updates: Record<string, unknown>) {
    setLocalConfig((prev) => (prev ? { ...prev, ...updates } : prev));
    setDirty(true);
  }

  function patchCouncil(updates: Record<string, unknown>) {
    patch({ council: { ...council, ...updates } });
  }

  async function handleSave() {
    if (!localConfig) return;
    setSaving(true);
    try {
      await updateConfig(localConfig);
      setDirty(false);
      toast.success("Configuration saved");
    } catch {
      toast.error("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  }

  if (loading && !config) {
    return (
      <div className="flex-1 p-8 max-w-6xl mx-auto w-full space-y-4">
        <Skeleton className="h-8 w-48 rounded-lg" />
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 lg:p-8 max-w-6xl mx-auto w-full animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--cc-text)] tracking-tight">Configuration</h1>
          <p className="text-sm text-[var(--cc-text-muted)] mt-1">
            Manage agents, providers, and analysis settings
          </p>
        </div>
        {dirty && (
          <Button onClick={handleSave} disabled={saving} className="hover-lift cursor-pointer">
            <Save className="w-4 h-4 mr-2" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        )}
      </div>

      <Tabs defaultValue="general">
        <TabsList className="mb-6">
          {[
            { value: "general", label: "General", icon: Settings },
            { value: "providers", label: "Providers", icon: Cpu },
            { value: "agents", label: "Agents", icon: Users },
            { value: "ingestion", label: "Ingestion", icon: FolderOpen },
            { value: "output", label: "Output", icon: FileOutput },
          ].map(({ value, label, icon: Icon }) => (
            <TabsTrigger key={value} value={value} className="flex items-center gap-1.5 cursor-pointer">
              <Icon className="w-3.5 h-3.5" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* ── General ── */}
        <TabsContent value="general">
          <div className="card-premium p-6 space-y-6">
            <SectionHeader title="Debate Settings" description="Configure how the multi-agent debate operates" icon={Settings} />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <FieldGroup label="Topology">
                <Select
                  value={(council.debate_topology as string) || "adversarial"}
                  onValueChange={(v) => v && patchCouncil({ debate_topology: v })}
                >
                  <SelectTrigger className="rounded-lg cursor-pointer">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["adversarial", "collaborative", "socratic", "open_floor", "panel", "custom"].map((t) => (
                      <SelectItem key={t} value={t} className="cursor-pointer capitalize">
                        {t.replace("_", " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldGroup>

              <FieldGroup label={`Debate Rounds: ${(council.max_rounds as number) || 3}`}>
                <input
                  type="range" min={1} max={10}
                  value={(council.max_rounds as number) || 3}
                  onChange={(e) => patchCouncil({ max_rounds: Number(e.target.value) })}
                  className="w-full accent-[var(--cc-accent)] cursor-pointer mt-1"
                />
              </FieldGroup>

              <FieldGroup label="Budget Limit ($)">
                <Input
                  type="number" min="0" step="1"
                  value={(council.budget_limit_usd as number) || ""}
                  onChange={(e) => patchCouncil({ budget_limit_usd: e.target.value ? parseFloat(e.target.value) : 0 })}
                  placeholder="No limit"
                  className="rounded-lg"
                />
              </FieldGroup>

              <FieldGroup label="Human-in-the-loop">
                <div className="mt-1">
                  <Toggle
                    enabled={!!council.hitl_enabled}
                    onChange={() => patchCouncil({ hitl_enabled: !council.hitl_enabled })}
                    label="HITL"
                  />
                </div>
              </FieldGroup>
            </div>
          </div>
        </TabsContent>

        {/* ── Providers ── */}
        <TabsContent value="providers">
          <div className="card-premium p-6">
            <SectionHeader title="Provider Configuration" description="Configure API keys and models for each provider" icon={Cpu} />
            <div className="space-y-3">
              {Object.entries(PROVIDER_META).map(([name, meta]) => {
                const conf = providers[name] || {};
                const Icon = meta.icon;
                const hasKey = !!(conf.api_key as string);
                return (
                  <div key={name} className={cn(
                    "rounded-xl border p-4 transition-all duration-200",
                    "bg-[var(--cc-bg)] hover:border-[var(--cc-border-hover)]",
                    hasKey ? "border-[var(--cc-border-hover)]" : "border-[var(--cc-border)]"
                  )}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-[var(--cc-bg-hover)] flex items-center justify-center">
                          <Icon className="w-4 h-4 text-[var(--cc-text-secondary)]" />
                        </div>
                        <span className="text-sm font-semibold capitalize text-[var(--cc-text)]">{name}</span>
                      </div>
                      {hasKey && (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[var(--cc-green-muted)]">
                          <Check className="w-3 h-3 text-[var(--cc-green)]" />
                          <span className="text-[10px] font-semibold text-[var(--cc-green)]">Configured</span>
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <FieldGroup label="API Key">
                        <Input
                          type="password"
                          value={(conf.api_key as string) || ""}
                          onChange={(e) => patch({
                            llm: { ...llm, providers: { ...providers, [name]: { ...conf, api_key: e.target.value } } }
                          })}
                          placeholder={meta.placeholder}
                          className="h-8 text-xs rounded-lg"
                        />
                      </FieldGroup>
                      <FieldGroup label="Model">
                        <Input
                          value={(conf.model as string) || ""}
                          onChange={(e) => patch({
                            llm: { ...llm, providers: { ...providers, [name]: { ...conf, model: e.target.value } } }
                          })}
                          placeholder="Default model"
                          className="h-8 text-xs rounded-lg"
                        />
                      </FieldGroup>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </TabsContent>

        {/* ── Agents ── */}
        <TabsContent value="agents">
          <div className="card-premium p-6">
            <SectionHeader title="Agent Configuration" description="Enable, disable, and configure individual agents" icon={Users} />
            <div className="space-y-3">
              {Object.entries(AGENTS_META).map(([handle]) => {
                const agentCfg = (agents[handle] ?? {}) as Record<string, unknown>;
                return (
                  <AgentCard
                    key={handle}
                    handle={handle}
                    agentCfg={agentCfg}
                    onUpdate={(agentPatch) => {
                      patch({ agents: { ...agents, [handle]: { ...agentCfg, ...agentPatch } } });
                    }}
                  />
                );
              })}
            </div>
          </div>
        </TabsContent>

        {/* ── Ingestion ── */}
        <TabsContent value="ingestion">
          <div className="card-premium p-6">
            <SectionHeader title="Ingestion Settings" description="Control how repositories are scanned and analysed" icon={FolderOpen} />
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FieldGroup label="Max Files">
                  <Input
                    type="number"
                    value={(ingest.max_files as number) || 500}
                    onChange={(e) => patch({ ingest: { ...ingest, max_files: Number(e.target.value) } })}
                    className="rounded-lg"
                  />
                </FieldGroup>
                <FieldGroup label="Max File Size (KB)">
                  <Input
                    type="number"
                    value={(ingest.max_file_size_kb as number) || 100}
                    onChange={(e) => patch({ ingest: { ...ingest, max_file_size_kb: Number(e.target.value) } })}
                    className="rounded-lg"
                  />
                </FieldGroup>
                <FieldGroup label="Git Log Limit">
                  <Input
                    type="number"
                    value={(ingest.git_log_limit as number) || 200}
                    onChange={(e) => patch({ ingest: { ...ingest, git_log_limit: Number(e.target.value) } })}
                    className="rounded-lg"
                  />
                </FieldGroup>
                <FieldGroup label="Features">
                  <div className="flex flex-wrap gap-2 mt-1">
                    {["AST Parse", "CVE Scan", "Secrets", "Licence", "Incremental"].map((feat) => {
                      const key = feat.toLowerCase().replace(" ", "_");
                      const active = (ingest[key] as boolean) !== false;
                      return (
                        <button
                          key={feat}
                          onClick={() => patch({ ingest: { ...ingest, [key]: !active } })}
                          className={cn(
                            "px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer transition-all duration-200",
                            active
                              ? "bg-[var(--cc-accent-muted)] border-[var(--cc-accent)] text-[var(--cc-accent)]"
                              : "bg-transparent border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:border-[var(--cc-border-hover)]"
                          )}
                        >
                          {active && <Check className="w-3 h-3 inline mr-1" />}
                          {feat}
                        </button>
                      );
                    })}
                  </div>
                </FieldGroup>
              </div>
              <FieldGroup label="Exclude Paths (one per line)">
                <textarea
                  className="w-full rounded-xl border border-[var(--cc-border)] px-3 py-2.5 text-xs resize-y font-mono bg-[var(--cc-bg-elevated)] text-[var(--cc-text)] placeholder:text-[var(--cc-text-muted)] focus:border-[var(--cc-accent)] focus:outline-none transition-all duration-200 min-h-[100px]"
                  rows={4}
                  value={((ingest.exclude_paths as string[]) || ["node_modules", ".git", "dist", "build"]).join("\n")}
                  onChange={(e) => patch({ ingest: { ...ingest, exclude_paths: e.target.value.split("\n").filter(Boolean) } })}
                  placeholder="node_modules&#10;.git&#10;dist"
                />
              </FieldGroup>
            </div>
          </div>
        </TabsContent>

        {/* ── Output ── */}
        <TabsContent value="output">
          <div className="card-premium p-6">
            <SectionHeader title="Output Settings" description="Configure RFC output formats and export options" icon={FileOutput} />
            <div className="space-y-5">
              <FieldGroup label="Output Formats">
                <div className="flex flex-wrap gap-2 mt-1">
                  {["markdown", "json", "html", "pdf"].map((fmt) => {
                    const formats = (lc.output_formats as string[]) || (lc.output as Record<string, unknown>)?.formats as string[] || ["markdown"];
                    const selected = formats.includes(fmt);
                    return (
                      <button
                        key={fmt}
                        onClick={() => {
                          const updated = selected ? formats.filter((f) => f !== fmt) : [...formats, fmt];
                          patch({ output: { ...((lc.output ?? {}) as Record<string, unknown>), formats: updated } });
                        }}
                        className={cn(
                          "px-4 py-2 rounded-lg text-sm font-semibold border cursor-pointer transition-all duration-200",
                          selected
                            ? "bg-[var(--cc-accent)] border-[var(--cc-accent)] text-white shadow-[0_2px_12px_rgba(108,92,231,0.3)]"
                            : "bg-transparent border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:border-[var(--cc-border-hover)] hover:text-[var(--cc-text)] hover:bg-[var(--cc-bg-hover)]"
                        )}
                      >
                        {selected && <Check className="w-3 h-3 inline mr-1.5" />}
                        {fmt.toUpperCase()}
                      </button>
                    );
                  })}
                </div>
              </FieldGroup>

              <FieldGroup label="Output Directory">
                <Input
                  value={((lc.output as Record<string, unknown>)?.directory as string) || "./output"}
                  onChange={(e) => patch({ output: { ...((lc.output ?? {}) as Record<string, unknown>), directory: e.target.value } })}
                  placeholder="./output"
                  className="rounded-lg font-mono text-xs"
                />
              </FieldGroup>

              <FieldGroup label="Webhook URL">
                <Input
                  value={((lc.output as Record<string, unknown>)?.webhook_url as string) || ""}
                  onChange={(e) => patch({ output: { ...((lc.output ?? {}) as Record<string, unknown>), webhook_url: e.target.value } })}
                  placeholder="https://hooks.example.com/codecouncil"
                  className="rounded-lg text-xs"
                />
              </FieldGroup>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Unsaved changes toast */}
      {dirty && (
        <div className="fixed bottom-6 right-6 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl glass border border-[var(--cc-accent)] glow-sm animate-fade-in z-50">
          <div className="w-2 h-2 rounded-full bg-[var(--cc-accent)] animate-pulse-glow" />
          <span className="text-sm text-[var(--cc-text-secondary)]">Unsaved changes</span>
          <Button size="sm" onClick={handleSave} disabled={saving} className="cursor-pointer">
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      )}
    </div>
  );
}
