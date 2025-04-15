#!/usr/bin/env python

def main():
    # Read the file content
    with open('llm_event_query.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for the fetch_market_data section within the analyze_historical_event function
    # Check if there's a try block without a matching except
    try_line = "        try:\n            df = fetch_market_data(ticker, event_date, end_date)"
    
    # Split content into lines
    lines = content.split('\n')
    
    try_except_count = 0
    in_function = False
    
    # First pass: Check if there are any missing "except" blocks
    for i, line in enumerate(lines):
        if "def analyze_historical_event" in line:
            in_function = True
            continue
        
        if in_function and "def generate_event_impact_explanation" in line:
            in_function = False
            continue
        
        if in_function:
            if line.strip() == "try:":
                try_except_count += 1
            elif line.strip().startswith("except "):
                try_except_count -= 1
    
    print(f"Try-except balance in analyze_historical_event: {try_except_count}")
    
    if try_except_count > 0:
        print(f"Found {try_except_count} try blocks without matching except blocks!")
        
        # Look for the specific problematic section
        fetch_line_index = -1
        for i, line in enumerate(lines):
            if "df = fetch_market_data(ticker, event_date, end_date)" in line:
                fetch_line_index = i
                break
        
        if fetch_line_index > 0:
            print(f"Found fetch_market_data call at line {fetch_line_index + 1}")
            
            # Check if the if df.empty: line is indented more than the try: line
            try_line_index = -1
            for i in range(fetch_line_index - 5, fetch_line_index):
                if lines[i].strip() == "try:":
                    try_line_index = i
                    break
            
            if_empty_index = -1
            for i in range(fetch_line_index, fetch_line_index + 5):
                if "if df.empty:" in lines[i]:
                    if_empty_index = i
                    break
            
            if try_line_index > 0 and if_empty_index > 0:
                try_indent = len(lines[try_line_index]) - len(lines[try_line_index].lstrip())
                if_indent = len(lines[if_empty_index]) - len(lines[if_empty_index].lstrip())
                
                print(f"Try line indent: {try_indent}, if df.empty indent: {if_indent}")
                
                if if_indent <= try_indent:
                    print("ISSUE: if df.empty: is not properly indented inside the try block!")
                    # Fix indentation
                    lines[if_empty_index] = " " * (try_indent + 4) + lines[if_empty_index].strip()
                    print(f"Fixed indentation: '{lines[if_empty_index]}'")
        
        # Write the fixed content
        with open('llm_event_query.py', 'w') as f:
            f.write('\n'.join(lines))
    
    print("Analysis and fix completed.")

if __name__ == "__main__":
    main() 