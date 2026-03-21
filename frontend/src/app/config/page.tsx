"use client";

import { useState, useEffect } from "react";
import { useConfigStore } from "@/stores/configStore";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
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
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-5 h-5" style={{ color: "var(--cc-accent)" }} />
        <h2 className="text-base font-semibold" style={{ color: "var(--cc-text)" }}>
          {title}
        </h2>
      </div>
      {description && (
        <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
          {description}
        </p>
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
      className="rounded-lg border overflow-hidden"
      style={{ borderColor: agent.enabled ? `${color}66` : "var(--cc-border)" }}
    >
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
        style={{ borderLeftWidth: 3, borderLeftColor: color, borderLeftStyle: "solid" }}
      >
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
              {agent.name}
            </span>
            <Badge
              variant="outline"
              className="text-xs"
              style={{ color, borderColor: `${color}44` }}
            >
              {agent.role}
            </Badge>
          </div>
          <div className="text-xs mt-0.5" style={{ color: "var(--cc-text-muted)" }}>
            {agent.provider} {agent.model && `· ${agent.model}`}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onUpdate(agent.id, { enabled: !agent.enabled });
            }}
            className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
            style={{ backgroundColor: agent.enabled ? color : "var(--cc-border)" }}
          >
            <span
              className={cn(
                "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform",
                agent.enabled ? "translate-x-4" : "translate-x-0.5"
              )}
            />
          </button>
          {expanded ? (
            <ChevronUp className="w-4 h-4" style={{ color: "var(--cc-text-muted)" }} />
          ) : (
            <ChevronDown className="w-4 h-4" style={{ color: "var(--cc-text-muted)" }} />
          )}
        </div>
      </div>

      {expanded && (
        <div
          className="px-4 pb-4 space-y-3 border-t"
          style={{ borderColor: "var(--cc-border)" }}
        >
          <div className="pt-3 grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs" style={{ color: "var(--cc-text-muted)" }}>Provider</label>
              <Input
                value={agent.provider}
                onChange={(e) => onUpdate(agent.id, { provider: e.target.value })}
                className="h-7 text-xs"
                style={{
                  backgroundColor: "var(--cc-bg)",
                  borderColor: "var(--cc-border)",
                  color: "var(--cc-text)",
                }}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs" style={{ color: "var(--cc-text-muted)" }}>Model Override</label>
              <Input
                value={agent.model || ""}
                onChange={(e) => onUpdate(agent.id, { model: e.target.value })}
                placeholder="(use provider default)"
                className="h-7 text-xs"
                style={{
                  backgroundColor: "var(--cc-bg)",
                  borderColor: "var(--cc-border)",
                  color: "var(--cc-text)",
                }}
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
    <div className="flex-1 p-6 max-w-4xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--cc-text)" }}>
            Configuration
          </h1>
          <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            Manage agents, providers, and analysis settings
          </p>
        </div>
        {dirty && (
          <Button
            onClick={handleSave}
            disabled={saving}
            style={{ backgroundColor: "var(--cc-accent)", color: "white" }}
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? "Saving…" : "Save Changes"}
          </Button>
        )}
      </div>

      <Tabs defaultValue="general">
        <TabsList
          className="mb-6"
          style={{ backgroundColor: "var(--cc-bg-card)" }}
        >
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
              className="flex items-center gap-1.5"
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* General */}
        <TabsContent value="general">
          <Card
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            <CardContent className="pt-6 space-y-6">
              <SectionHeader
                title="Debate Settings"
                description="Configure how the multi-agent debate operates"
                icon={Settings}
              />

              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                    Topology
                  </label>
                  <Select
                    value={localConfig?.topology || "round_robin"}
                    onValueChange={(v) => v && patch({ topology: v })}
                  >
                    <SelectTrigger style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)", color: "var(--cc-text)" }}>
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
                  <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                    Debate Rounds: {localConfig?.debate_rounds || 3}
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={10}
                    value={localConfig?.debate_rounds || 3}
                    onChange={(e) => patch({ debate_rounds: Number(e.target.value) })}
                    className="w-full"
                    style={{ accentColor: "var(--cc-accent)" }}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                    Budget Limit ($)
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="1"
                    value={localConfig?.budget_limit || ""}
                    onChange={(e) => patch({ budget_limit: e.target.value ? parseFloat(e.target.value) : undefined })}
                    placeholder="No limit"
                    style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                    Human-in-the-loop
                  </label>
                  <div className="flex items-center gap-3 mt-2">
                    <button
                      onClick={() => patch({ hitl_enabled: !localConfig?.hitl_enabled })}
                      className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                      style={{
                        backgroundColor: localConfig?.hitl_enabled
                          ? "var(--cc-accent)"
                          : "var(--cc-border)",
                      }}
                    >
                      <span
                        className={cn(
                          "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                          localConfig?.hitl_enabled ? "translate-x-6" : "translate-x-1"
                        )}
                      />
                    </button>
                    <span className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
                      {localConfig?.hitl_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Providers */}
        <TabsContent value="providers">
          <Card style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)" }}>
            <CardContent className="pt-6">
              <SectionHeader
                title="Provider Configuration"
                description="Configure API keys and models for each provider"
                icon={Cpu}
              />
              <div className="space-y-4">
                {["openai", "anthropic", "gemini", "ollama"].map((provider) => {
                  const conf = (localConfig?.providers || {})[provider] || {};
                  return (
                    <div
                      key={provider}
                      className="rounded-lg border p-4 space-y-3"
                      style={{ borderColor: "var(--cc-border)", backgroundColor: "var(--cc-bg)" }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium capitalize" style={{ color: "var(--cc-text)" }}>
                          {provider}
                        </span>
                        {conf.api_key && (
                          <Check className="w-4 h-4" style={{ color: "var(--cc-green)" }} />
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-xs" style={{ color: "var(--cc-text-muted)" }}>API Key</label>
                          <Input
                            type="password"
                            value={(conf as { api_key?: string }).api_key || ""}
                            onChange={(e) =>
                              patch({
                                providers: {
                                  ...(localConfig?.providers || {}),
                                  [provider]: { ...conf, api_key: e.target.value },
                                },
                              })
                            }
                            placeholder={provider === "ollama" ? "N/A" : "sk-…"}
                            className="h-7 text-xs"
                            style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs" style={{ color: "var(--cc-text-muted)" }}>Model</label>
                          <Input
                            value={(conf as { model?: string }).model || ""}
                            onChange={(e) =>
                              patch({
                                providers: {
                                  ...(localConfig?.providers || {}),
                                  [provider]: { ...conf, model: e.target.value },
                                },
                              })
                            }
                            placeholder="Default model"
                            className="h-7 text-xs"
                            style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Agents */}
        <TabsContent value="agents">
          <Card style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)" }}>
            <CardContent className="pt-6">
              <SectionHeader
                title="Agent Configuration"
                description="Enable, disable, and configure individual agents"
                icon={Users}
              />
              <div className="space-y-3">
                {(localConfig?.agents || []).length === 0 ? (
                  <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
                    No agents configured. Default agents will be used.
                  </p>
                ) : (
                  (localConfig?.agents || []).map((agent) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      onUpdate={(id, agentPatch) => {
                        patch({
                          agents: (localConfig?.agents || []).map((a) =>
                            a.id === id ? { ...a, ...agentPatch } : a
                          ),
                        });
                      }}
                    />
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Ingestion */}
        <TabsContent value="ingestion">
          <Card style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)" }}>
            <CardContent className="pt-6">
              <SectionHeader
                title="Ingestion Settings"
                description="Control how code is ingested and chunked for analysis"
                icon={FolderOpen}
              />
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>Max File Size (bytes)</label>
                    <Input
                      type="number"
                      value={localConfig?.ingestion?.max_file_size || 1048576}
                      onChange={(e) =>
                        patch({ ingestion: { ...localConfig?.ingestion, max_file_size: Number(e.target.value) } })
                      }
                      style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>Chunk Size</label>
                    <Input
                      type="number"
                      value={localConfig?.ingestion?.chunk_size || 4096}
                      onChange={(e) =>
                        patch({ ingestion: { ...localConfig?.ingestion, chunk_size: Number(e.target.value) } })
                      }
                      style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                    Excluded Patterns (one per line)
                  </label>
                  <textarea
                    className="w-full rounded-md border px-3 py-2 text-xs resize-y"
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
                    style={{
                      backgroundColor: "var(--cc-bg)",
                      borderColor: "var(--cc-border)",
                      color: "var(--cc-text)",
                      fontFamily: "var(--font-geist-mono)",
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Output */}
        <TabsContent value="output">
          <Card style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)" }}>
            <CardContent className="pt-6">
              <SectionHeader
                title="Output Settings"
                description="Configure output formats and export options"
                icon={FileOutput}
              />
              <div className="space-y-3">
                <label className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
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
                        className="px-3 py-1.5 rounded-md text-sm font-medium border transition-colors"
                        style={{
                          backgroundColor: selected ? "var(--cc-accent)" : "transparent",
                          borderColor: selected ? "var(--cc-accent)" : "var(--cc-border)",
                          color: selected ? "white" : "var(--cc-text-muted)",
                        }}
                      >
                        {selected && <Check className="w-3 h-3 inline mr-1" />}
                        {fmt.toUpperCase()}
                      </button>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {dirty && (
        <div
          className="fixed bottom-6 right-6 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border"
          style={{
            backgroundColor: "var(--cc-bg-card)",
            borderColor: "var(--cc-accent)",
          }}
        >
          <span className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            You have unsaved changes
          </span>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving}
            style={{ backgroundColor: "var(--cc-accent)", color: "white" }}
          >
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      )}
    </div>
  );
}
