import json
import sys
import os
from agent_reviewer import review_code
from agent_tester import generate_tests
from agent_documenter import generate_documentation

def run_multi_agent_system(file_path):
    """Orchestrate all three agents"""
    
    print("=" * 50)
    print("MULTI-AGENT CODE AUDITOR SYSTEM")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return
    
    # Read the code
    with open(file_path, 'r', encoding='utf-8') as f:
        code_content = f.read()
    
    print(f"\nAnalyzing: {file_path}")
    print(f"Code size: {len(code_content)} characters\n")
    
    # Step 1: Review the code
    print("AGENT 1: Code Reviewer - Analyzing...")
    review_result = review_code(file_path)
    
    if "error" in review_result:
        print(f"Review failed: {review_result['error']}")
        return
    
    print(f"Review complete!")
    print(f"   - Bugs found: {len(review_result.get('bugs', []))}")
    print(f"   - Style issues: {len(review_result.get('style_issues', []))}")
    print(f"   - Security risks: {len(review_result.get('security_risks', []))}")
    
    # Step 2: Generate tests
    print("\nAGENT 2: Test Generator - Creating test suite...")
    test_code = generate_tests(code_content, review_result)
    print(f"Test suite saved to: test_suite.py")
    
    # Step 3: Generate documentation
    print("\nAGENT 3: Documentation Writer - Creating README...")
    readme_content = generate_documentation(code_content, test_code)
    print(f"README saved to: README.md")
    
    # Final summary
    print("\n" + "=" * 50)
    print("MULTI-AGENT SYSTEM COMPLETE!")
    print("=" * 50)
    print(f"\nOutput files created:")
    print(f"   1. review_report.md  - Detailed code analysis")
    print(f"   2. test_suite.py     - Pytest unit tests")
    print(f"   3. README.md         - Project documentation")
    print(f"\nTo run tests: pytest test_suite.py -v")
    
    # Optional: Show the summary from review
    if 'summary' in review_result:
        print(f"\nReview Summary: {review_result['summary']}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_multi_agent_system(sys.argv[1])
    else:
        print("Usage: python main.py <file_to_analyze>")
        print("\nExample: python main.py buggy_code.py")
