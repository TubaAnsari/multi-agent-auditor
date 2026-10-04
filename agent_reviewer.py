import json
import requests
from ollama_client import query_ollama

def review_code(file_path):
    """Read a code file and analyze it for issues"""
    
    # Read the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code_content = f.read()
    except FileNotFoundError:
        return {"error": f"File {file_path} not found"}
    
    # Check file size - warn if too large
    if len(code_content) > 50000:
        print(f"Warning: File is large ({len(code_content)} chars). Analysis may take time...")
    
    # Truncate code if extremely large (over 30k chars)
    if len(code_content) > 30000:
        code_content = code_content[:30000] + "\n# ... [rest of file truncated for analysis]"
        print(f"Truncated file to 30,000 characters for analysis")
    
    # Create prompt for the AI (simplified for better response)
    prompt = f"""Analyze this Python code and return ONLY valid JSON.

Code:
{code_content}

Return this exact JSON structure:
{{
    "bugs": ["list each bug found, be specific"],
    "style_issues": ["list style problems"],
    "security_risks": ["list security concerns"],
    "performance": ["list performance issues"],
    "summary": "one sentence overall assessment"
}}

If no issues in a category, return empty list []. Only return valid JSON, no other text."""

    # Get AI analysis
    print("  Calling Ollama (this may take 30-60 seconds)...")
    response = query_ollama(prompt)
    
    # Check for errors
    if response.startswith("Error:"):
        result = {
            "bugs": [response],
            "style_issues": [],
            "security_risks": [],
            "performance": [],
            "summary": "Analysis failed due to timeout or connection issue. Try a smaller file."
        }
    else:
        # Try to parse JSON response
        try:
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                result = json.loads(json_str)
            else:
                result = json.loads(response)
        except:
            # Fallback if JSON parsing fails
            result = {
                "bugs": ["Could not parse AI response"],
                "style_issues": [],
                "security_risks": [],
                "performance": [],
                "summary": response[:200] if not response.startswith("Error:") else "Analysis failed"
            }
    
    # Save report to file
    with open('review_report.md', 'w', encoding='utf-8') as f:
        f.write(f"# Code Review Report\n\n")
        f.write(f"## Summary\n{result.get('summary', 'N/A')}\n\n")
        f.write(f"## Bugs Found\n")
        for bug in result.get('bugs', []):
            f.write(f"- {bug}\n")
        f.write(f"\n## Style Issues\n")
        for style in result.get('style_issues', []):
            f.write(f"- {style}\n")
        f.write(f"\n## Security Risks\n")
        for risk in result.get('security_risks', []):
            f.write(f"- {risk}\n")
        f.write(f"\n## Performance Issues\n")
        for perf in result.get('performance', []):
            f.write(f"- {perf}\n")
    
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = review_code(sys.argv[1])
        print(json.dumps(result, indent=2))
        print(f"\n Report saved to: review_report.md")
    else:
        print("Usage: python agent_reviewer.py <file_path>")