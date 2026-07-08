# 🌌 Project Nexus - System Design

**Version:** Nexus 2.0.0-alpha.1

---

# Overview

Project Nexus is a modular AI platform designed primarily for Discord.

The system is built around the idea that every component should have one responsibility.

Every feature should be replaceable without rewriting the entire application.

---

# Core Principles

## 1. Single Responsibility

Every module has one purpose.

Examples:

- AI Engine → AI orchestration
- Provider Manager → AI provider selection
- Conversation Manager → Conversation building
- Database → Data storage
- Commands → Discord commands
- Logger → Logging

---

## 2. Modular Design

Every system should be replaceable.

Example:

Gemini

↓

Groq

↓

OpenRouter

↓

OpenAI

without changing the Discord bot.

---

## 3. Separation of Concerns

Discord never talks directly to AI providers.

Discord

↓

AI Engine

↓

Conversation Manager

↓

Provider Manager

↓

AI Provider

---

## 4. Configuration First

Nothing should be hardcoded.

Everything configurable belongs inside:

config.py

or

Settings Manager.

---

# System Architecture

Discord

↓

Bot

↓

AI Engine

↓

Conversation Manager

↓

Provider Manager

↓

Gemini / Groq / OpenRouter

---

# Memory Flow

User Message

↓

Conversation Manager

↓

Load System Prompt

↓

Load User Profile

↓

Load Memories

↓

Load Facts

↓

Build Conversation

↓

Provider

↓

AI Response

↓

Save Memory

---

# AI Providers

Every provider must inherit from:

BaseProvider

Required function:

ask(
    user_id,
    conversation
)

Providers:

- Gemini
- Groq
- OpenRouter
- OpenAI

---

# User Profiles

Every Discord user owns one profile.

A profile contains:

- User ID
- Username
- Display Name
- Role
- Nicknames
- Facts
- Preferences
- Statistics
- Created Date
- Last Seen

---

# Roles

Creator

↓

Izumi

(Rohit / IZ)

---

Special User

↓

Ash

(Ashey)

---

Admin

↓

Server Staff

---

User

↓

Everyone Else

---

# Future Systems

Planned Features

- Voice Chat
- Image Generation
- Web Search
- Google Drive Backup
- Supabase Database
- Dashboard
- Plugin System
- Event System
- Analytics
- Multi-Provider AI

---

# Development Philosophy

Build once.

Extend forever.

Never rewrite because of poor architecture.

Only expand.

---

# Project Motto

Project Nexus is designed to become more than a Discord bot.

It is an extensible AI platform that can grow into multiple applications while keeping one unified architecture.
