import requests
import enum
import logging
logger = logging.getLogger("harness.llm")


class llmtype(enum.Enum):
    ols = "ols"
    judge = "judge"

class LLM:
    def __init__(self, url: str, token: str, type: llmtype = llmtype.ols, model: str = None, provider: str = None, conversation_id: str = None ):
        self.url = url
        self.token = token
        self.type = type
        self.model = model
        self.provider = provider
        self.conversation_id = conversation_id
        logger.info(f"[Initialization] Type: [{llmtype(self.type).name}] Model: [{self.model}]")

    def query(self, prompt: str, temperature: int = 0, response_format: dict = {"type": "json_object"}) -> str:
        logger.debug(f"Querying LLM of type [{llmtype(self.type).name}], model: [{self.model}] at [{self.url}]")
        logger.debug(f"Prompt: [{prompt}]")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {}
        if self.type == llmtype.ols:
            payload["query"] = "In TrilioVault for Kubernetes, " +prompt + "Do not use any tools."
            if self.provider:
                payload["provider"] = self.provider
            if self.conversation_id:
                payload["conversation_id"] = self.conversation_id
        else:
            payload["messages"] = [{"role": "user", "content": prompt + " Do not use any tools."}]
            if temperature:
                payload['temperature'] = temperature
            if response_format:
                payload['response_format'] = response_format
        if self.model:
            payload["model"] = self.model
        response = requests.post(f"{self.url}", json=payload, headers=headers, verify=False)
        if response.status_code != 200:
            logger.error(f"Request to LLM failed with error: {response.text}")
        return response.json()
