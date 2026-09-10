from crewai import LLM

from .. import config


def default_llm() -> LLM:
    return LLM(model="gpt-4o-mini", api_key=config.OPENAI_API_KEY)
