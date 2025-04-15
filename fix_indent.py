#!/usr/bin/env python

def main():
    # Read the file content
    with open('llm_event_query.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the problematic line - we know it's around line 917
    for i in range(910, 920):
        print(f"Line {i}: {lines[i-1].rstrip()}")
    
    # Potential issue: If the 'else:' is misplaced in line 916
    # Let's check if there's an indentation issue
    if lines[915].strip() == 'else:':
        print("Found the 'else:' at line 916, checking indentation...")
        
        # Since we're targeting that specific else, let's ensure it has the right indentation
        if not lines[915].startswith('    '):  # Should have 4 spaces for proper indentation
            print("Fixing indentation of 'else:' at line 916")
            lines[915] = '    else:\n'  # Correcting with 4 spaces indentation
    
    # Write the fixed content back
    with open('llm_event_query.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fix attempted. Run the streamlit app to see if it works.")

if __name__ == "__main__":
    main() 