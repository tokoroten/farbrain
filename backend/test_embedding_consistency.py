import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.embedding import EmbeddingService
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

async def main():
    service = EmbeddingService()

    # Test text
    test_text = "会議を減らす"

    print(f"Testing embedding consistency for: '{test_text}'")
    print()

    # Generate embedding twice
    embedding1 = await service.embed(test_text)
    embedding2 = await service.embed(test_text)

    # Calculate cosine similarity
    similarity = cosine_similarity(
        embedding1.reshape(1, -1),
        embedding2.reshape(1, -1)
    )[0][0]

    print(f"Embedding 1 shape: {embedding1.shape}")
    print(f"Embedding 2 shape: {embedding2.shape}")
    print(f"First 5 values of embedding 1: {embedding1[:5]}")
    print(f"First 5 values of embedding 2: {embedding2[:5]}")
    print()
    print(f"Cosine similarity: {similarity:.6f}")
    print()

    if similarity > 0.999:
        print("✓ Embeddings are IDENTICAL (as expected)")
    elif similarity > 0.95:
        print("⚠ Embeddings are similar but not identical")
    else:
        print("✗ Embeddings are DIFFERENT (ERROR!)")

    # Now test with a slightly different text
    print()
    print("Testing with different text...")
    different_text = "会議を増やす"
    embedding3 = await service.embed(different_text)

    similarity_diff = cosine_similarity(
        embedding1.reshape(1, -1),
        embedding3.reshape(1, -1)
    )[0][0]

    print(f"Text 1: '{test_text}'")
    print(f"Text 2: '{different_text}'")
    print(f"Cosine similarity: {similarity_diff:.6f}")
    print()

    if similarity_diff < 0.9:
        print("✓ Different texts have DIFFERENT embeddings (as expected)")
    else:
        print("⚠ Different texts have very similar embeddings")

if __name__ == "__main__":
    asyncio.run(main())
