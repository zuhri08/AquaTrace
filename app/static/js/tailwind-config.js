window.tailwind = window.tailwind || {};
window.tailwind.config = {
  theme: {
    extend: {
      colors: {
        aqua: {
          ink: "#1C1E21",
          muted: "#5D6C7B",
          border: "#CED0D4",
          canvas: "#FFFFFF",
          soft: "#F1F4F7",
          cobalt: "#0064E0",
          critical: "#E41E3F",
          telemetry: "#6A3DE8"
        }
      },
      fontFamily: {
        sans: ["Montserrat", "Helvetica", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"]
      },
      borderRadius: {
        "aqua-card": "24px"
      }
    }
  }
};
