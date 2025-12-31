const path = require("path");
const { defineConfig } = require("vite");
const react = require("@vitejs/plugin-react");

module.exports = defineConfig({
  root: path.join(__dirname, "src", "renderer"),
  plugins: [react()],
  base: "./",
  build: {
    outDir: path.join(__dirname, "dist", "renderer"),
    emptyOutDir: true
  },
  server: {
    port: 5173
  }
});
