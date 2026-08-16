"""Pydantic request/response schemas for the Zero-Code Playwright Generator API.

This module is the EXPLICIT contract between the React frontend and the FastAPI
backend. Field names here MUST match:
  - the keys in the `fetch` JSON body sent by `ZeroCodeTestGenerator.jsx`
  - the state setter fields consumed by the React dashboard after the response

Contract verification checklist (grep both sides to confirm no drift):
  | Field           | Frontend (ZeroCodeTestGenerator.jsx)              | Backend (models.py)             |
  |-----------------|---------------------------------------------------|---------------------------------|
  | url             | state `url`  -> fetch body                         | `GenerateTestRequest.url`       |
  | instructions    | state `instructions` -> fetch body                | `GenerateTestRequest.instructions`|
  | session_storage | state `sessionStorageInput` -> parsed JSON in body| `GenerateTestRequest.session_storage`|
  | status          | derived from `data.status`                        | `GenerateTestResponse.status`   |
  | script          | stored via `setGeneratedScript(data.script)`      | `GenerateTestResponse.script`    |
  | dom_snapshot    | optional preview                                  | `GenerateTestResponse.dom_snapshot`|
  | error           | stored via `setErrorMsg(data.error)`              | `GenerateTestResponse.error`     |
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, HttpUrl, Field


class GenerateTestRequest(BaseModel):
    """Inbound payload from the React dashboard.

    Attributes:
        url:             Target website the LLM should write a test against.
        instructions:    Natural-language description of the E2E test scenario.
        session_storage: Optional Playwright `storageState` JSON (cookies +
                          localStorage) used to bypass login walls before DOM
                          extraction. Schema matches Playwright's native format:
                          {"cookies": [...], "origins": [{"localStorage": [...]}]}.
                          If None, the headless browser navigates anonymous.
        provider:        AI provider name (e.g., NVIDIA NIM, OpenRouter, OpenAI, Anthropic).
        model:           Model identifier for the selected provider.
        user_api_key:    Optional user‑supplied API key (BYOK).
    """

    url: HttpUrl = Field(..., description="Target page URL to extract and test.")
    instructions: str = Field(
        ..., min_length=1, description="Natural-language test scenario."
    )
    session_storage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional Playwright storageState JSON for authenticated sessions.",
    )
    provider: str = Field(default="NVIDIA NIM", description="AI provider name.")
    model: str = Field(default="nvidia/nemotron-3-ultra-550b-a55b", description="Model identifier.")
    user_api_key: Optional[str] = Field(default=None, description="User supplied API key (BYOK).")


class GenerateTestResponse(BaseModel):
    """Outbound payload returned to the React dashboard.

    `status` is always present. Exactly one of (`script`, `error`) is populated
    depending on the outcome. `dom_snapshot` is informational and only included
    on success so the UI can show what the LLM saw.
    """

    status: Literal["success", "error"] = Field(..., description="Result disposition.")
    script: Optional[str] = Field(
        default=None, description="Generated Python Playwright async script."
    )
    dom_snapshot: Optional[str] = Field(
        default=None, description="Compressed text DOM tree extracted from the target page."
    )
    error: Optional[str] = Field(default=None, description="Human-readable failure message.")


class GeneratePOMRequest(BaseModel):
    """Inbound payload for role‑based POM generation.

    Attributes:
        environment: Target environment (Dev, QA, UAT).
        role: User role that drives test data / permissions (MCS, PAT, Manager, BA).
        language: Target automation language (TypeScript, JavaScript, Python, Java).
        login_url: Authentication entry point (optional for public sites).
        username: Credentials – username (optional).
        password: Credentials – password (optional, sent over HTTPS only).
        target_url: Internal page to exercise after login.
        instructions: Natural‑language test scenario.
        provider: AI provider name (e.g., NVIDIA NIM, OpenRouter, OpenAI, Anthropic).
        model: Model identifier for the selected provider.
        user_api_key: Optional user‑supplied API key (BYOK).
    """

    environment: Literal["Dev", "QA", "UAT"] = Field(..., description="Target environment.")
    role: Literal["MCS", "PAT", "Manager", "BA"] = Field(..., description="User role.")
    language: Literal["TypeScript", "JavaScript", "Python", "Java"] = Field(..., description="Target automation language.")
    login_url: Optional[str] = Field(default="", description="Login page URL (optional for public sites).")
    username: str = Field(default="", min_length=0, description="Username for authentication (optional).")
    password: str = Field(default="", min_length=0, description="Password for authentication (optional).")
    target_url: HttpUrl = Field(..., description="Target page URL after login.")
    instructions: str = Field(..., min_length=1, description="Natural‑language test scenario.")
    provider: str = Field(default="NVIDIA NIM", description="AI provider name.")
    model: str = Field(default="nvidia/nemotron-3-ultra-550b-a55b", description="Model identifier.")
    user_api_key: Optional[str] = Field(default=None, description="User supplied API key (BYOK).")


class GeneratePOMResponse(BaseModel):
    """Outbound payload containing generated Page‑Object Model and test suite."""

    pom_code: str = Field(..., description="Generated page_objects.py content.")
    test_code: str = Field(..., description="Generated test_suite.py content.")


class CreateSessionRequest(BaseModel):
    """Inbound payload for creating an authenticated session."""
    environment: str = Field(..., description="Target environment.")
    role: str = Field(..., description="User role.")
    login_url: HttpUrl = Field(..., description="Login page URL.")
    username: str = Field(..., min_length=1, description="Username for authentication.")
    password: str = Field(..., min_length=1, description="Password for authentication.")
    provider: str = Field(default="NVIDIA NIM", description="AI provider name.")
    model: str = Field(default="nvidia/nemotron-3-ultra-550b-a55b", description="Model identifier.")
    user_api_key: Optional[str] = Field(default=None, description="User supplied API key (BYOK).")
