# Prompt Guide

## Principles

- Keep repository rules and output shape in prompt templates.
- Keep sensitive values out of prompts.
- Render prompts from structured data collected by agents.

## Template Contract

Each prompt should specify:

- role
- objective
- input summary
- required output format
- constraints

## Fallback Policy

If no LLM response is available, agents publish the deterministic fallback generated from their collected data.
