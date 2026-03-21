import { create } from "zustand";
import type { AppConfig } from "@/lib/types";
import { getConfig, updateConfig } from "@/lib/api";

interface ConfigState {
  config: AppConfig | null;
  loading: boolean;
  error: string | null;
  loadConfig: () => Promise<void>;
  updateConfig: (patch: Partial<AppConfig>) => Promise<void>;
}

const DEFAULT_CONFIG: AppConfig = {
  providers: {},
  agents: [],
  topology: "round_robin",
  debate_rounds: 3,
  hitl_enabled: false,
  output_formats: ["markdown"],
  ingestion: {
    max_file_size: 1048576,
    excluded_patterns: ["node_modules", ".git", "*.min.js"],
    chunk_size: 4096,
  },
};

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  loading: false,
  error: null,

  loadConfig: async () => {
    set({ loading: true, error: null });
    try {
      const config = await getConfig();
      set({ config, loading: false });
    } catch (e) {
      // Use defaults if API not available
      set({ config: DEFAULT_CONFIG, loading: false, error: String(e) });
    }
  },

  updateConfig: async (patch: Partial<AppConfig>) => {
    set({ loading: true, error: null });
    try {
      const config = await updateConfig(patch);
      set({ config, loading: false });
    } catch (e) {
      set({ loading: false, error: String(e) });
      throw e;
    }
  },
}));
