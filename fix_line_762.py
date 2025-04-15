#!/usr/bin/env python

def main():
    # Read the file content
    with open('llm_event_query.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Print the line in question and surrounding lines
    print("Examining line 762 and surrounding lines:")
    for i in range(758, 767):
        if i < len(lines):
            print(f"Line {i+1}: {lines[i].rstrip()}")
    
    # Check if there's an if statement immediately after a try statement
    try_followed_by_if = False
    for i in range(len(lines) - 1):
        if lines[i].strip() == "try:" and "if" in lines[i+1]:
            print(f"\nFound try: immediately followed by if at lines {i+1}-{i+2}")
            print(f"  Line {i+1}: {lines[i].rstrip()}")
            print(f"  Line {i+2}: {lines[i+1].rstrip()}")
            try_followed_by_if = True
    
    if not try_followed_by_if:
        print("\nNo issues found with try-if structure.")
    
    # Fix specific line 762 if it's the 'if df.empty:' line
    if 761 < len(lines) and "if df.empty:" in lines[761]:
        # Check indentation
        line_indent = len(lines[761]) - len(lines[761].lstrip())
        
        # Find the previous try statement
        try_line_index = -1
        for i in range(761, 750, -1):
            if lines[i].strip() == "try:":
                try_line_index = i
                break
        
        if try_line_index != -1:
            try_indent = len(lines[try_line_index]) - len(lines[try_line_index].lstrip())
            
            if line_indent <= try_indent:
                print(f"\nISSUE: line 762 'if df.empty:' has incorrect indentation ({line_indent} spaces) compared to try line ({try_indent} spaces)")
                # Fix by increasing indentation
                correct_indent = try_indent + 4  # Add 4 spaces to the try indentation
                lines[761] = " " * correct_indent + "if df.empty:\n"
                print(f"Fixed line 762 to: {lines[761].rstrip()}")
                
                # Write the fixed content back
                with open('llm_event_query.py', 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print("File updated with the fix.")
            else:
                print(f"\nLine 762 'if df.empty:' has correct indentation ({line_indent} spaces) compared to try line ({try_indent} spaces)")
    
    print("\nAnalysis completed.")

if __name__ == "__main__":
    main() 