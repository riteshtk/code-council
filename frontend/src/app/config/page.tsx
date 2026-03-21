"use client";

import { useState, useEffect } from "react";
import { useConfigStore } from "@/stores/configStore";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
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
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { AGENT_COLORS } from "@/lib/utils";

function SectionHeader({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-5 h-5 text-[var(--cc-accent)]" />
        <h2 className="text-base font-semibold text-[var(--cc-text)]">{title}</h2>
      </div>
      {description && (
        <p className="text-sm text-[var(--cc-text-muted)]">{description}</p>
      )}
    </div>
  );
}

function AgentCard({ agent, onUpdate }: {
  agent: { id: string; name: string; role: string; provider: string; enabled: boolean; model?: string };
  onUpdate: (id: string, patch: Partial<typeof agent>) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const color = Object.entries(AGENT_COLORS).find(([k]) =>
    agent.id.toLowerCase().includes(k)
  )?.[1] || "var(--cc-accent)";

  return (
    <div
      className={cn(
        "rounded-xl overflow-hidden transition-all duration-300 border-l-4",
        agent.enabled
          ? "border border-[var(--cc-border-hover)] bg-[var(--cc-bg)]"
          : "border border-[var(--cc-border)] bg-[var(--cc-bg)]"
      )}
      style={{ borderLeftColor: color }}
    >
      <div
        className="flex items-center gap-3 px-4 py-3.5 cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-300"
        onClick={() => setExpanded(!expanded)}
      >
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
          style={{ backgroundColor: `color-mix(in srgb, ${color} 18%, transparent)` }}
        >
          <span className="text-sm font-bold" style={{ color }}>{agent.name.charAt(4)}</span>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--cc-text)]">
              {agent.name}
            </span>
            <Badge
              variant="outline"
              className="text-xs"
              style={{ color, borderColor: `color-mix(in srgb, ${color} 30%, transparent)` }}
            >
              {agent.role}
            </Badge>
          </div>
          <div className="text-xs mt-0.5 text-[var(--cc-text-muted)]">
            {agent.provider} {agent.model && `· ${agent.model}`}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onUpdate(agent.id, { enabled: !agent.enabled });
            }}
            className="relative inline-flex h-5 w-9 items-center rounded-full cursor-pointer transition-colors duration-300"
            style={{ backgroundColor: agent.enabled ? color : "var(--cc-bg-active)" }}
          >
            <span
              className={cn(
                "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-300",
                agent.enabled ? "translate-x-4" : "translate-x-0.5"
              )}
            />
          </button>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-[var(--cc-text-muted)]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[var(--cc-text-muted)]" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[var(--cc-border)] animate-fade-in">
          <div className="pt-3 grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">Provider</label>
              <Input
                value={agent.provider}
                onChange={(e) => onUpdate(agent.id, { provider: e.target.value })}
                className="h-8 text-xs rounded-lg"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">Model Override</label>
              <Input
                value={agent.model || ""}
                onChange={(e) => onUpdate(agent.id, { model: e.target.value })}
                placeholder="(use provider default)"
                className="h-8 text-xs rounded-lg"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ConfigPage() {
  const { config, loading, loadConfig, updateConfig } = useConfigStore();
  const [dirty, setDirty] = useState(false);
  const [localConfig, setLocalConfig] = useState(config);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    setLocalConfig(config);
  }, [config]);

  // Helper to read nested config safely (supports both flat and nested shapes)
  function cfg(key: string): unknown {
    if (!localConfig) return undefined;
    const lc = localConfig as unknown as Record<string, unknown>;
    // Try flat key first
    if (key in lc) return lc[key];
    // Try nested: council.*, llm.*, ingest.*, output.*
    const councilMap: Record<string, string> = {
      topology: "debate_topology", debate_topology: "debate_topology",
      debate_rounds: "max_rounds", max_rounds: "max_rounds",
      budget_limit: "budget_limit_usd", budget_limit_usd: "budget_limit_usd",
      hitl_enabled: "hitl_enabled",
    };
    if (councilMap[key]) {
      const council = lc.council as Record<string, unknown> | undefined;
      return council?.[councilMap[key]];
    }
    return undefined;
  }

  function patch(updates: Record<string, unknown>) {
    setLocalConfig((prev) => (prev ? { ...prev, ...updates } : prev));
    setDirty(true);
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
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 lg:p-8 max-w-4xl mx-auto w-full animate-fade-in">
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
            <TabsTrigger
              key={value}
              value={value}
              className="flex items-center gap-1.5 cursor-pointer"
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* General */}
        <TabsContent value="general">
          <div className="card-premium p-6">
            <SectionHeader
              title="Debate Settings"
              description="Configure how the multi-agent debate operates"
              icon={Settings}
            />

            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Topology
                </label>
                <Select
                  value={(cfg("topology") as string) || "adversarial"}
                  onValueChange={(v) => v && patch({ topology: v })}
                >
                  <SelectTrigger className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["round_robin", "adversarial", "panel", "socratic"].map((t) => (
                      <SelectItem key={t} value={t}>{t.replace("_", " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Rounds: <span className="text-[var(--cc-accent)] font-bold">{(cfg("max_rounds") as number) || 3}</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={(cfg("max_rounds") as number) || 3}
                  onChange={(e) => patch({ council: { ...((localConfig as unknown as Record<string, unknown>)?.council as Record<string, unknown> || {}), max_rounds: Number(e.target.value) } })}
                  className="w-full accent-[var(--cc-accent)] cursor-pointer"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Budget Limit ($)
                </label>
                <Input
                  type="number"
                  min="0"
                  step="1"
                  value={(cfg("budget_limit_usd") as number) || ""}
                  onChange={(e) => patch({ budget_limit: e.target.value ? parseFloat(e.target.value) : undefined })}
                  placeholder="No limit"
                  className="rounded-lg"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Human-in-the-loop
                </label>
                <div className="flex items-center gap-3 mt-2">
                  <button
                    onClick={() => patch({ hitl_enabled: !cfg("hitl_enabled") })}
                    className={cn(
                      "relative inline-flex h-6 w-11 items-center rounded-full cursor-pointer transition-colors duration-300",
                      cfg("hitl_enabled") ? "bg-[var(--cc-accent)]" : "bg-[var(--cc-bg-active)]"
                    )}
                  >
                    <span
                      className={cn(
                        "inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-300",
                        cfg("hitl_enabled") ? "translate-x-6" : "translate-x-1"
                      )}
                    />
                  </button>
                  <span className="text-sm text-[var(--cc-text-secondary)]">
                    {cfg("hitl_enabled") ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Providers */}
        <TabsContent value="providers">
          <div className="card-premium p-6">
            <SectionHeader
              title="Provider Configuration"
              description="Configure API keys and models for each provider"
              icon={Cpu}
            />
            <div className="space-y-4">
              {["openai", "anthropic", "gemini", "ollama"].map((provider) => {
                const llmProviders = (localConfig as unknown as Record<string, unknown>)?.llm as Record<string, unknown> | undefined;
                const providersMap = (llmProviders?.providers || localConfig?.providers || {}) as Record<string, Record<string, unknown>>;
                const conf = providersMap[provider] || {} as Record<string, string>;
                return (
                  <div
                    key={provider}
                    className="rounded-xl border border-[var(--cc-border)] p-4 space-y-3 bg-[var(--cc-bg)] hover:border-[var(--cc-border-hover)] transition-all duration-300"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold capitalize text-[var(--cc-text)]">
                        {provider}
                      </span>
                      {(conf as Record<string, string>).api_key && (
                        <div className="flex items-center gap-1.5">
                          <Check className="w-4 h-4 text-[var(--cc-green)]" />
                          <span className="text-xs text-[var(--cc-green)]">Configured</span>
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">API Key</label>
                        <Input
                          type="password"
                          value={(conf as { api_key?: string }).api_key || ""}
                          onChange={(e) =>
                            patch({
                              providers: {
                                ...providersMap,
                                [provider]: { ...conf, api_key: e.target.value },
                              },
                            })
                          }
                          placeholder={provider === "ollama" ? "N/A" : "sk-..."}
                          className="h-8 text-xs rounded-lg"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">Model</label>
                        <Input
                          value={(conf as { model?: string }).model || ""}
                          onChange={(e) =>
                            patch({
                              providers: {
                                ...providersMap,
                                [provider]: { ...conf, model: e.target.value },
                              },
                            })
                          }
                          placeholder="Default model"
                          className="h-8 text-xs rounded-lg"
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </TabsContent>

        {/* Agents */}
        <TabsContent value="agents">
          <div className="card-premium p-6">
            <SectionHeader
              title="Agent Configuration"
              description="Enable, disable, and configure individual agents"
              icon={Users}
            />
            <div className="space-y-3">
              {(() => {
                const agentsObj = localConfig?.agents || {};
                const agentsList = Array.isArray(agentsObj)
                  ? agentsObj
                  : Object.entries(agentsObj)
                      .filter(([k]) => k !== "custom")
                      .map(([handle, cfg]) => ({
                        id: handle,
                        name: `The ${handle.charAt(0).toUpperCase() + handle.slice(1)}`,
                        role: handle,
                        provider: (cfg as Record<string, unknown>)?.provider as string || "default",
                        model: (cfg as Record<string, unknown>)?.model as string || "",
                        enabled: (cfg as Record<string, unknown>)?.enabled !== false,
                      }));
                return agentsList.length === 0 ? (
                  <p className="text-sm text-[var(--cc-text-muted)] py-4">
                    No agents configured. Default agents will be used.
                  </p>
                ) : (
                  agentsList.map((agent) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      onUpdate={(id, agentPatch) => {
                        const current = localConfig?.agents || {};
                        if (!Array.isArray(current) && typeof current === "object") {
                          patch({
                            agents: {
                              ...current,
                              [id]: { ...(current as Record<string, unknown>)[id] as Record<string, unknown>, ...agentPatch },
                            },
                          });
                        }
                      }}
                    />
                  ))
                );
              })()}
            </div>
          </div>
        </TabsContent>

        {/* Ingestion */}
        <TabsContent value="ingestion">
          <div className="card-premium p-6">
            <SectionHeader
              title="Ingestion Settings"
              description="Control how code is ingested and chunked for analysis"
              icon={FolderOpen}
            />
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                    Max File Size (bytes)
                  </label>
                  <Input
                    type="number"
                    value={localConfig?.ingestion?.max_file_size || 1048576}
                    onChange={(e) =>
                      patch({ ingestion: { ...localConfig?.ingestion, max_file_size: Number(e.target.value) } })
                    }
                    className="rounded-lg"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                    Chunk Size
                  </label>
                  <Input
                    type="number"
                    value={localConfig?.ingestion?.chunk_size || 4096}
                    onChange={(e) =>
                      patch({ ingestion: { ...localConfig?.ingestion, chunk_size: Number(e.target.value) } })
                    }
                    className="rounded-lg"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Excluded Patterns (one per line)
                </label>
                <textarea
                  className="w-full rounded-xl border border-[var(--cc-border)] px-3 py-2.5 text-xs resize-y font-mono bg-[var(--cc-bg-elevated)] text-[var(--cc-text)] focus:border-[var(--cc-accent)] focus:outline-none focus:ring-0 transition-all duration-300"
                  rows={5}
                  value={(localConfig?.ingestion?.excluded_patterns || []).join("\n")}
                  onChange={(e) =>
                    patch({
                      ingestion: {
                        ...localConfig?.ingestion,
                        excluded_patterns: e.target.value.split("\n").filter(Boolean),
                      },
                    })
                  }
                />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Output */}
        <TabsContent value="output">
          <div className="card-premium p-6">
            <SectionHeader
              title="Output Settings"
              description="Configure output formats and export options"
              icon={FileOutput}
            />
            <div className="space-y-3">
              <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                Output Formats
              </label>
              <div className="flex flex-wrap gap-2">
                {["markdown", "json", "html", "pdf"].map((fmt) => {
                  const selected = (localConfig?.output_formats || []).includes(fmt);
                  return (
                    <button
                      key={fmt}
                      onClick={() => {
                        const current = localConfig?.output_formats || [];
                        patch({
                          output_formats: selected
                            ? current.filter((f) => f !== fmt)
                            : [...current, fmt],
                        });
                      }}
                      className={cn(
                        "px-4 py-2 rounded-lg text-sm font-medium border cursor-pointer transition-all duration-300",
                        selected
                          ? "bg-[var(--cc-accent)] border-[var(--cc-accent)] text-white shadow-[0_2px_12px_rgba(108,92,231,0.35)]"
                          : "bg-transparent border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:border-[var(--cc-border-hover)] hover:text-[var(--cc-text)] hover:bg-[var(--cc-bg-hover)]"
                      )}
                    >
                      {selected && <Check className="w-3 h-3 inline mr-1.5" />}
                      {fmt.toUpperCase()}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {dirty && (
        <div className="fixed bottom-6 right-6 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl border glass border-[var(--cc-accent)] glow-sm animate-fade-in">
          <span className="text-sm text-[var(--cc-text-secondary)]">
            You have unsaved changes
          </span>
          <Button size="sm" onClick={handleSave} disabled={saving} className="cursor-pointer">
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      )}
    </div>
  );
}
