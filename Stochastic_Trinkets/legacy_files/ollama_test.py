import ollama

trinket_namer_modelfile='''
FROM gemma2:2b
PARAMETER temperature 0.9
SYSTEM You are tasked with deciding names of gamefiles in the video game Darkest Dungeon. Answer only with a plausible name for the game file and nothing else.
'''

ollama.create(model='trinket_namer', modelfile=trinket_namer_modelfile)
print('model loaded')

response = ollama.chat(model='trinket_namer', messages=[
  {
    'role': 'user',
    'content': 'What is a good name for a trinket, in line with the themes of the game?',
  },
])
print(response['message']['content'])
