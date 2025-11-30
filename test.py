def add(a, b):
    return a - b

# from llama_cpp import Llama

# print("Loading model...")
# llm = Llama(
#     model_path="C:/Users/amanp/.codedoc/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
#     n_gpu_layers=20,   # Move 20 layers to GPU, adjust according to VRAM
#     n_ctx=4096
# )

# print("Generating...")
# output = llm(
#     "Write a python hello world program:",
#     max_tokens=200,
#     stop=["<|endoftext|>"]
# )

# print(output["choices"][0]["text"])
