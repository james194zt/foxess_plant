import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/foxess-plant-panel.ts"),
      formats: ["es"],
      fileName: () => "foxess-plant-panel.js",
    },
    outDir: resolve(__dirname, "../custom_components/foxess_plant/www"),
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
