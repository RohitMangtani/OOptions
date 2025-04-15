#!/usr/bin/env python
import ast
import sys

def check_syntax(file_path):
    """Check if the Python file has valid syntax by parsing it into an AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Try to parse the file
        ast.parse(source)
        print(f"✅ {file_path} has valid syntax!")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}:")
        print(f"  Line {e.lineno}, column {e.offset}")
        print(f"  {e.text.strip()}")
        print(f"  {' ' * (e.offset - 1)}^")
        print(f"  {e.msg}")
        
        # Print some context
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, e.lineno - 5)
            end = min(len(lines), e.lineno + 5)
            print("\nContext:")
            for i in range(start, end):
                print(f"{i+1:4d}: {lines[i].rstrip()}")
        except Exception as e2:
            print(f"Error showing context: {e2}")
        
        return False
    except Exception as e:
        print(f"❌ Error checking syntax: {str(e)}")
        return False

if __name__ == "__main__":
    file_path = "llm_event_query.py"
    result = check_syntax(file_path)
    sys.exit(0 if result else 1) 