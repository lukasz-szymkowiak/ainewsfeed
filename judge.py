import json

import anthropic
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

build_judge_prompt = '''You are an expert fact-checker. You will be given a claim and source text. Your task is to analyze whether source text supports the claim.
Use only given source text for verificaiton.  '''

def build_prompt(claim: str, source_text: str) -> str:
    return f"""{build_judge_prompt} <claim> {claim} </claim> \n Source text: <source> {source_text} </source> 
            return only a JSON object with two keys: 'supported' (boolean) and 'reason' (string). 
            If the source text supports the claim, set 'supported' to true and provide a brief reason.
              If it does not support the claim, set 'supported' to false and provide a brief reason. 
              If the source text is insufficient to determine support, 
              set 'supported' to false and provide a reason indicating that the source text is insufficient. Paraphrases are fine, but do not add any information that is not present in the source text.
              The JSON object should be the only output, and it should be valid JSON."""



def parse_judge_reply(reply: str) -> dict:
    """Turn the judge's raw text into {"supported": bool, "reason": str}.

    Raises ValueError if the reply isn't valid JSON or has the wrong shape.
    """
    try:
        data = json.loads(reply)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    if not isinstance(data.get("supported"), bool):
        raise ValueError("'supported' missing or not a boolean")
    if not isinstance(data.get("reason"), str):
        raise ValueError("'reason' missing or not a string")

    return {"supported": data["supported"], "reason": data["reason"]}

def call_claude(prompt: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    hist = []
    hist.append({"role": "user", "content": prompt})
    hist.append({"role": "assistant", "content": response.content[0].text})
    reply_llm = response.content[0].text
    try:
        reply_llm = parse_judge_reply(reply_llm)
    except ValueError:
        response2 = client.messages.create(
                model="claude-haiku-5-5",
                max_tokens=1500,
                messages=[{"role": "user", "content": "bad output, please return only a JSON object with two keys: 'supported' (boolean) and 'reason' (string)."}],
            )
        reply_llm = response2.content[0].text

    return reply_llm

if __name__ == "__main__":
    reply = call_claude(build_prompt("hello", "world"))
    print(type(reply))
    print(parse_judge_reply(reply))

