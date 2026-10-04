import json
from ollama_client import query_ollama
import os
def generate_documentation(code_content, test_content):
    """Generate professional README documentation"""
    
    prompt = f"""You are a technical documentation expert. Create a professional README.md for this code.

CODE:
{code_content[:3000]}

TESTS:
{test_content[:2000]}

Generate a complete README.md with these sections:
1. **Project Title** (appropriate name based on the code)
2. **Description** (what this code does)
3. **Installation** (pip install pytest, etc.)
4. **Usage Examples** (show how to use the functions)
5. **API Reference** (document each function)
6. **Running Tests** (pytest command)
7. **Known Issues** (based on bugs found)

Format in proper markdown. Use code blocks for examples. Be professional and thorough."""

    # Generate documentation
    readme_content = query_ollama(prompt)
    
    # Clean up markdown if needed
    if "```markdown" in readme_content:
        readme_content = readme_content.split("```markdown")[1].split("```")[0]
    elif "```" in readme_content and readme_content.startswith("```"):
        readme_content = readme_content.split("```")[1].split("```")[0]
    
    # Save to file
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    return readme_content

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        code_file = sys.argv[1]
        test_file = sys.argv[2] if len(sys.argv) > 2 else 'test_suite.py'
        
        # Read the code file
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Read the test file
        with open(test_file, 'r', encoding='utf-8') as f:
            tests = f.read()
        
        print("Generating documentation...")
        docs = generate_documentation(code, tests)
        print("README.md created!")
    else:
        print("Usage: python agent_documenter.py <code_file> [test_file]")
