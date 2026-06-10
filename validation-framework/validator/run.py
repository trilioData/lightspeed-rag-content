from validatePrompt import ValidatePrompt
import argparse
import os
import yaml
import json
from llm import LLM, llmtype
import constants
from logger import logger
from prompts import Prompt
import urllib3
from report import print_full_report
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


OLS_URL = os.getenv("OLS_URL")
token = os.getenv("TOKEN")
groq_key = os.getenv("GROQ_KEY")
OLS_MODEL = os.getenv("OLS_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
OLS_PROVIDER = os.getenv("OLS_PROVIDER")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def main():
    parser = argparse.ArgumentParser(description="Validate prompts")
    parser.add_argument("-p", "--prompt", required=False, help="Single prompt file")
    parser.add_argument("-d", "--dir", required=False, help="Directory of prompt files")
    args = parser.parse_args()

    ols = LLM(OLS_URL, token, type=llmtype.ols, 
              model=OLS_MODEL, provider=OLS_PROVIDER)
    llmjudge = LLM(constants.groq_rest_api, groq_key, 
                    type=llmtype.judge, model=GROQ_MODEL)

    # Collect prompt files
    prompt_files = []
    if args.prompt:
        prompt_files.append(args.prompt)
    elif args.dir:
        for root, dirs, files in os.walk(args.dir):
            for f in sorted(files):
                if f.endswith((".yaml", ".yml")):
                    prompt_files.append(os.path.join(root, f))

    logger.info(f"Running {len(prompt_files)} prompts")

    all_results = []
    for i, pf in enumerate(prompt_files):
        with open(pf, "r") as f:
            prompt = Prompt(**yaml.safe_load(f))
        
        logger.info(f"[{i+1}/{len(prompt_files)}]")
        response = ols.query(prompt.prompt)
        vp = ValidatePrompt(prompt, response, llmjudge)
        result = vp.validate()
        result["prompt_file"] = pf
        all_results.append(result)

    print_full_report(all_results, threshold=0.6)


if __name__ == "__main__":
    import logging
    logger = logging.getLogger("harness.promptValidator")
    main()