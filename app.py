import chainlit as cl
import openai
import asyncio
import json
import os
import base64
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT

# Load environment variables
load_dotenv()

configurations = {
    "mistral_7B_instruct": {
        "endpoint_url": os.getenv("MISTRAL_7B_INSTRUCT_ENDPOINT"),
        "api_key": os.getenv("RUNPOD_API_KEY"),
        "model": "mistralai/Mistral-7B-Instruct-v0.2"
    },
    "mistral_7B": {
        "endpoint_url": os.getenv("MISTRAL_7B_ENDPOINT"),
        "api_key": os.getenv("RUNPOD_API_KEY"),
        "model": "mistralai/Mistral-7B-v0.1"
    },
    "openai_gpt-4": {
        "endpoint_url": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4"
    }
}

# Choose configuration
config_key = "openai_gpt-4"
# config_key = "mistral_7B_instruct"
#config_key = "mistral_7B"

# Get selected configuration
config = configurations[config_key]

from langsmith.wrappers import wrap_openai
from langsmith import traceable

# Initialize the OpenAI async client
# client = openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"])
client = wrap_openai(openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"]))

gen_kwargs = {
    "model": config["model"],
    "temperature": 0.3,
    "max_tokens": 500
}

# Configuration setting to enable or disable the system prompt
ENABLE_SYSTEM_PROMPT = True

@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])

    if ENABLE_SYSTEM_PROMPT and (not message_history or message_history[0].get("role") != "system"):
        system_prompt_content = SYSTEM_PROMPT
        message_history.insert(0, {"role": "system", "content": system_prompt_content})

    message_history.append({"role": "user", "content": message.content})

    #asyncio.create_task(assess_message(message_history))
    
    response_message = cl.Message(content="")
    await response_message.send()

    if config_key == "mistral_7B":
        stream = await client.completions.create(prompt=message.content, stream=True, **gen_kwargs)
        async for part in stream:
            if token := part.choices[0].text or "":
                await response_message.stream_token(token)
    else:
        stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
        async for part in stream:
            if token := part.choices[0].delta.content or "":
                await response_message.stream_token(token)

    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)
    await response_message.update()


if __name__ == "__main__":
    cl.main()