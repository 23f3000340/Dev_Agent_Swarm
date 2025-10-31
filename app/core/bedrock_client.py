# app/core/bedrock_client.py
import boto3, json, asyncio
from typing import Dict, Any, Optional
from app.config import settings

class BedrockOrchestrator:
    def __init__(self, region: str = None, model_id: str = None):
        self.region = region or settings.AWS_REGION
        self.model_id = model_id or settings.BEDROCK_MODEL_ID
        self.rt = boto3.client("bedrock-runtime", region_name=self.region)
        self.agent_rt = boto3.client("bedrock-agent-runtime", region_name=self.region)

    async def health_check(self) -> bool:
        try:
            # light ping: list minimal info, avoids large payloads
            self.rt.list_foundation_models(maxResults=5)
            return True
        except Exception:
            return False

    def invoke_model(self, prompt: str, max_tokens: int = 1024) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-06-01",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = self.rt.invoke_model(modelId=self.model_id, body=body)
        data = json.loads(resp["body"].read())
        return data["content"][0]["text"]

    async def invoke_supervisor_agent(
        self,
        session_id: str,
        input_text: str,
        agent_id: Optional[str] = None,
        alias_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        agent_id = agent_id or settings.BEDROCK_SUPERVISOR_AGENT_ID
        alias_id = alias_id or settings.BEDROCK_AGENT_ALIAS_ID
        if not agent_id or not alias_id:
            # Fallback to direct model if agents not configured yet
            txt = self.invoke_model(input_text)
            return {"mode": "model", "assessment": txt}

        resp = self.agent_rt.invoke_agent(
            agentId=agent_id, agentAliasId=alias_id, sessionId=session_id, inputText=input_text
        )
        assessment = []
        for evt in resp.get("events", []):
            payload = evt.get("payload") or {}
            if "text" in payload:
                assessment.append(payload["text"])
        return {"mode": "agent", "assessment": "\n".join(assessment)}
