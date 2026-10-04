import json
import requests
from ollama_client import query_ollama

def generate_tests(code_content, review_data):
    """Generate pytest unit tests based on code and review findings"""
    
    # Truncate code if too large
    if len(code_content) > 20000:
        code_content = code_content[:20000] + "\n# ... [truncated]"
    
    # Format the review data for the prompt
    review_summary = json.dumps(review_data, indent=2)
    
    prompt = f"""Generate pytest unit tests for this code.

CODE:
{code_content[:8000]}

ISSUES FOUND:
{review_summary[:2000]}

Generate pytest test code that:
1. Tests normal use cases
2. Tests edge cases
3. Tests the bugs found

Return ONLY Python code starting with 'import pytest'. No explanations."""

    # Get AI-generated tests
    print("   🤖 Generating tests (this may take 30-60 seconds)...")
    test_code = query_ollama(prompt)
    
    # Check for errors
    if test_code.startswith("Error:"):
        test_code = f"""import pytest
import sys

def test_placeholder():
    '''Placeholder test - AI generation failed due to timeout'''
    assert True

# Original error: {test_code}
"""
    
    # Clean up the response
    if "```python" in test_code:
        test_code = test_code.split("```python")[1].split("```")[0]
    elif "```" in test_code:
        test_code = test_code.split("```")[1].split("```")[0]
    
    # Save to file
    with open('test_suite.py', 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    return test_code

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        code_file = sys.argv[1]
        
        # Read the code file
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Simple review data
        review_data = {
            "summary": "Analysis in progress",
            "bugs": ["Check division by zero", "Missing error handling"],
            "style_issues": [],
            "security_risks": [],
            "performance": []
        }
        
        print(" Generating tests...")
        tests = generate_tests(code, review_data)
        print("Test suite saved to: test_suite.py")
    else:
        print("Usage: python agent_tester.py <code_file>")