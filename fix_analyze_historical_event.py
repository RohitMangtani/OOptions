#!/usr/bin/env python

def main():
    # Read the file content
    with open('llm_event_query.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the start of the function
    function_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('def analyze_historical_event'):
            function_start = i
            break
    
    if function_start == 0:
        print("Could not find analyze_historical_event function")
        return
    
    print(f"Found function start at line {function_start + 1}")
    
    # Validate the try-except structure
    # Find the first 'try:' after function_start
    first_try = 0
    for i in range(function_start, len(lines)):
        if lines[i].strip() == 'try:':
            first_try = i
            break
    
    if first_try == 0:
        print("Could not find main try block")
        return
    
    print(f"Found main try block at line {first_try + 1}")
    
    # Find the nested try block for fetch_market_data
    fetch_market_try = 0
    for i in range(first_try, len(lines)):
        if 'fetch_market_data' in lines[i] and 'try:' in lines[i-1]:
            fetch_market_try = i - 1
            break
    
    if fetch_market_try == 0:
        print("Could not find fetch_market_data try block")
        return
    
    print(f"Found fetch_market_data try block at line {fetch_market_try + 1}")
    
    # Check if the indentation is correct in the fetch_market_data try block and its contents
    # The try block should be indented 8 spaces (inside the main try block)
    if not lines[fetch_market_try].startswith('        try:'):
        print(f"Incorrect indentation in fetch_market_data try block: '{lines[fetch_market_try].rstrip()}'")
        lines[fetch_market_try] = '        try:\n'
        print("Fixed indentation of try block")
    
    # Ensure the if/else blocks inside this try are indented correctly
    for i in range(fetch_market_try + 1, fetch_market_try + 30):  # Check the next 30 lines
        if 'if df.empty:' in lines[i]:
            if not lines[i].startswith('            '):  # Should be indented 12 spaces
                print(f"Incorrect indentation in 'if df.empty:' at line {i+1}: '{lines[i].rstrip()}'")
                lines[i] = '            if df.empty:\n'
                print("Fixed indentation of if df.empty: block")
    
    # Find the except block for fetch_market_data
    fetch_market_except = 0
    for i in range(fetch_market_try, len(lines)):
        if 'except Exception as e:' in lines[i] and 'Error fetching market data' in lines[i+1]:
            fetch_market_except = i
            break
    
    if fetch_market_except == 0:
        print("Could not find fetch_market_data except block")
        return
    
    print(f"Found fetch_market_data except block at line {fetch_market_except + 1}")
    
    # Check if the except block is indented correctly
    if not lines[fetch_market_except].startswith('        except'):
        print(f"Incorrect indentation in fetch_market_data except block: '{lines[fetch_market_except].rstrip()}'")
        lines[fetch_market_except] = '        except Exception as e:\n'
        print("Fixed indentation of except block")
    
    # Write the fixed content back
    with open('llm_event_query.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fix attempted. Run the streamlit app to see if it works.")

if __name__ == "__main__":
    main() 