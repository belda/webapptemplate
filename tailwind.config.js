/** @type {import('tailwindcss').Config} */
// Replaces the former in-browser Play CDN (cdn.tailwindcss.com), which is not
// built for production: it ships a compiler to every visitor, and some
// Safari/WebKit builds silently drop comma-containing arbitrary utilities
// (e.g. grid-cols-[minmax(0,1fr)_auto]) so layouts collapse on Apple devices
// only. This config drives a real build via the standalone Tailwind CLI, so the
// stylesheet is precompiled and deterministic across browsers.
//
// content MUST include apps/**/*.py and static/js/**/*.js: Tailwind only keeps
// classes it can find by scanning, and class strings are routinely built in
// Python (badge/status helpers) and in vanilla JS — none of which appear
// literally in any template. Drop those globs and those elements lose their
// styling in production. For the same reason, never build a class name by
// string concatenation; write it out literally.
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./webapptemplate/templates/**/*.html",
    "./apps/**/*.py",
    "./webapptemplate/**/*.py",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff", 100: "#dbeafe", 200: "#bfdbfe", 300: "#93c5fd",
          400: "#60a5fa", 500: "#3b82f6", 600: "#2563eb", 700: "#1d4ed8",
          800: "#1e40af", 900: "#1e3a8a", 950: "#172554",
        },
      },
    },
  },
};
