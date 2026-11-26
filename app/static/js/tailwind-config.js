window.tailwind = window.tailwind || {};
window.tailwind.config = {
  theme: {
    extend: {
      colors: {
        aqua: {
          canvas: "#ffffff",
          "surface-soft": "#f1f4f7",
          "ink-deep": "#0a1317",
          ink: "#1c1e21",
          charcoal: "#444950",
          slate: "#4b4c4f",
          steel: "#5d6c7b",
          stone: "#8595a4",
          hairline: "#ced0d4",
          "hairline-soft": "#dee3e9",
          "disabled-text": "#bcc0c4",
          "ink-button": "#000000",
          primary: "#0064e0",
          "primary-deep": "#0457cb",
          "primary-soft": "#0091ff",
          "fb-blue": "#1876f2",
          "selected-border": "#0143b5",
          "oculus-purple": "#a121ce",
          success: "#31a24c",
          "success-soft": "#e7f5eb",
          warning: "#f7b928",
          "warning-soft": "#fff4d6",
          attention: "#f2a918",
          critical: "#e41e3f",
          "critical-strong": "#f0284a",
          "critical-soft": "#ffeaed",
          "telemetry-soft": "#f8e9fc"
        }
      },
      fontFamily: {
        sans: ["Montserrat", "Helvetica", "Arial", "Noto Sans", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"]
      },
      fontWeight: {
        light: "300",
        normal: "400",
        medium: "500",
        bold: "700"
      },
      fontSize: {
        hero: ["64px", { lineHeight: "1.16", fontWeight: "500" }],
        display: ["48px", { lineHeight: "1.17", fontWeight: "500" }],
        "heading-lg": ["36px", { lineHeight: "1.28", fontWeight: "500" }],
        "heading-md": ["28px", { lineHeight: "1.21", fontWeight: "300" }],
        "heading-sm": ["24px", { lineHeight: "1.25", fontWeight: "500" }],
        sub: ["18px", { lineHeight: "1.44" }],
        body: ["16px", { lineHeight: "1.5" }],
        "body-sm": ["14px", { lineHeight: "1.43" }],
        caption: ["12px", { lineHeight: "1.33" }]
      },
      letterSpacing: {
        body: "-0.16px",
        "body-sm": "-0.14px"
      },
      lineHeight: {
        body: "1.5",
        "body-sm": "1.43"
      },
      borderRadius: {
        xs: "2px",
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "16px",
        xxl: "24px",
        xxxl: "32px",
        feature: "40px",
        full: "100px",
        circle: "50%"
      },
      spacing: {
        1: "4px",
        2: "8px",
        2.5: "10px",
        3: "12px",
        4: "16px",
        5: "20px",
        6: "24px",
        8: "32px",
        10: "40px",
        12: "48px",
        16: "64px",
        20: "80px",
        30: "120px"
      },
      screens: {
        xs: "480px",
        sm: "768px",
        md: "1024px",
        lg: "1360px"
      },
      boxShadow: {
        sticky: "0 1px 4px rgba(20, 22, 26, .3)"
      }
    }
  }
};
