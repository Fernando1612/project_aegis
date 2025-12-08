import google.generativeai as genai
from google.generativeai import types
from google.generativeai import protos
import inspect

print("GenAI Version:", genai.__version__)

print("\n--- Inspecting Tool Class ---")
print(inspect.signature(types.Tool))
print(types.Tool.__doc__)

print("\n--- Inspecting Protos Tool ---")
# Protos usually hold the raw fields
print(dir(protos.Tool))

print("\n--- Inspecting Protos GoogleSearch ---")
# Check if GoogleSearch proto exists
if hasattr(protos, 'GoogleSearch'):
    print("protos.GoogleSearch found!")
else:
    print("protos.GoogleSearch NOT found")

if hasattr(protos, 'GoogleSearchRetrieval'):
    print("protos.GoogleSearchRetrieval found!")
