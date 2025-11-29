# 🧠 CodeDoc — Local AI Code Repair & Refactor Assistant

CodeDoc is a lightweight, privacy-preserving AI tool that automatically **analyzes**, **fixes**, and **refactors source code** using a **smol-agent architecture** powered by **llama.cpp**, running fully offline.  
It improves developer productivity by identifying issues, optimizing structure, and validating functionality — without exposing code to external cloud services.

---

## 🚀 Features
- 🔍 Automatic code smell & issue detection
- ✨ AI-powered refactoring and optimization
- 🧪 Local test execution & validation (pytest-based)
- 🔐 100% offline inference with **llama.cpp**
- 🤖 Multi-agent reasoning workflow using **smol-agents**
- 📦 Code diff & export capability
- 🖥 Simple and clean UI using Streamlit (or CLI mode)

---

## 🧠 System Architecture

```text
                     ┌───────────────────────────────┐
                     │           Frontend             │
                     │      (Streamlit / CLI UI)      │
                     └───────────────────────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       smol-agents       │
                         └─────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌──────────────────┐       ┌───────────────────────┐    ┌───────────────────────┐
│ Analyzer Agent    │       │ Refactor Agent         │    │ Test Runner Agent      │
│ Static checks     │       │ llama.cpp inference     │    │ runs pytest / executes │
│ smells, unused    │       │ produces improved code  │    │ returns pass/fail      │
└──────────────────┘       └───────────────────────┘    └───────────────────────┘
                                      │
                                      ▼
                           ┌───────────────────────┐
                           │      Output Engine    │
                           │ diff + explanation    │
                           └───────────────────────┘
                                      │
                                      ▼
                           ┌───────────────────────┐
                           │     Final Result      │
                           └───────────────────────┘
