import requests
import os
import json
import sys

# Configuration
MCP_URL = os.getenv("MCP_SERVER_URL", "http://mcp_wrapper:8000")

def test_tool(tool_name, args={}):
    print(f"Testing tool: {tool_name} with args: {args}")
    print(f"Target URL: {MCP_URL}/tools/call")
    
    try:
        payload = {
            "name": tool_name,
            "arguments": args
        }
        resp = requests.post(f"{MCP_URL}/tools/call", json=payload)
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print("\nRaw Response:")
            print(json.dumps(data, indent=2))
            
            # Attempt to parse inner content if it's the standard MCP format
            if isinstance(data, list) and len(data) > 0 and data[0].get("type") == "text":
                print("\nParsed Content:")
                try:
                    inner_content = json.loads(data[0]["text"])
                    print(json.dumps(inner_content, indent=2))
                except:
                    print(data[0]["text"])
        else:
            print(f"Error: {resp.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    tool = sys.argv[1] if len(sys.argv) > 1 else "fetch_market_data"
    test_tool(tool)
