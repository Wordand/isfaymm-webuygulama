try:
    print("Testing model load...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("Model loaded successfully!")
    encoded = model.encode("Test metni")
    print(f"Encoding successful, shape: {encoded.shape}")
except Exception as e:
    print(f"Error: {e}")
