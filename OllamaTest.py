from ollama import generate

response = generate('gemma3:1b', 'Why is the sky blue?')
print(response['response'])