"""FastAPI server for Zero-Code Playwright Generator."""

from __future__ import annotations

import os
import sys
import asyncio
import json
from typing import Any, Dict, Optional

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from models import (
    GenerateTestRequest,
    GenerateTestResponse,
    GeneratePOMRequest,
    GeneratePOMResponse,
    CreateSessionRequest,
)
from playwright_service import extract_dom_context, extract_authenticated_dom, create_session
from prompts import build_user_prompt, SYSTEM_PROMPT, build_pom_user_prompt
from llm_router import create_async_client, _should_enable_reasoning


app = FastAPI(title="Zero-Code Playwright Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://zero-code-playwright-generator-tmw7.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/generate-test", response_model=GenerateTestResponse)
async def generate_test(request: GenerateTestRequest) -> GenerateTestResponse:
    try:
        html_context = await extract_dom_context(
            url=str(request.url),
            storage_state=request.session_storage,
            wait_until="domcontentloaded",
            timeout=60000,
        )
        # Create dynamic client per request
        client = create_async_client(request.provider, request.model, request.user_api_key)
        user_prompt = build_user_prompt(request.instructions, html_context)
        extra_body = {}
        if _should_enable_reasoning(request.model):
            extra_body = {
                "chat_template_kwargs": {"enable_thinking": True},
                "reasoning_budget": 16384,
            }
        response = await client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            extra_body=extra_body,
            temperature=0.1,
            max_tokens=8192,
        )
        script = response.choices[0].message.content.strip()
        return GenerateTestResponse(
            status="success",
            script=script,
            dom_snapshot=html_context,
        )
    except Exception as e:
        return GenerateTestResponse(
            status="error",
            error=str(e),
        )


@app.post("/generate-pom", response_model=GeneratePOMResponse)
async def generate_pom(request: GeneratePOMRequest) -> GeneratePOMResponse:
    try:
        # Determine if authentication is required
        login_url = (request.login_url or "").strip()
        if login_url:
            # Authenticated flow
            html_context = await extract_authenticated_dom(
                login_url=login_url,
                username=request.username or "",
                password=request.password or "",
                target_url=str(request.target_url),
            )
        else:
            # Public site – navigate directly to target_url
            html_context = await extract_dom_context(
                url=str(request.target_url),
                storage_state=None,
                wait_until="domcontentloaded",
                timeout=60000,
            )
        # Dynamic client for POM generation
        client = create_async_client(request.provider, request.model, request.user_api_key)
        user_prompt = build_pom_user_prompt(
            request.environment,
            request.role,
            request.language,
            request.instructions,
            html_context,
        )
        extra_body = {}
        if _should_enable_reasoning(request.model):
            extra_body = {
                "chat_template_kwargs": {"enable_thinking": True},
                "reasoning_budget": 16384,
            }
        response = await client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            extra_body=extra_body,
            temperature=0.1,
            max_tokens=8192,
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        pom_code = data["pom_code"]
        test_code = data["test_code"]
        return GeneratePOMResponse(pom_code=pom_code, test_code=test_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/create-session")
async def create_session_endpoint(request: CreateSessionRequest):
    try:
        success = await create_session(
            login_url=str(request.login_url),
            username=request.username,
            password=request.password,
        )
        if success:
            return {"status": "success", "message": "Session verified"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))