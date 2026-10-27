import anthropic
from dotenv import load_dotenv

load_dotenv()

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

def call_claude(prompt: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


if __name__ == "__main__":
    print(call_claude(build_prompt("hello", "world")))
    
