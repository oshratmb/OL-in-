import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 5173 },
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        profile: "profile.html",
        dashboard: "dashboard.html",
        jobIntake: "job-intake.html",
        qnaWizard: "qna-wizard.html",
        documentPreview: "document-preview.html",
        settings: "settings.html",
        interviewSimulator: "interview-simulator.html",
        simulationFeedback: "simulation-feedback.html",
        mfa: "mfa.html",
        admin: "admin.html",
      },
    },
  },
});
