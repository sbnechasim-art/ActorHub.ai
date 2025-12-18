#!/usr/bin/env python3
"""
InsightFace Model Setup Script

Downloads and configures the buffalo_l model for face recognition.
Run this once before starting the API in production.

Usage:
    python scripts/setup_insightface.py
"""

import os
import sys
from pathlib import Path

def setup_insightface():
    """Download and verify InsightFace model."""
    print("=" * 60)
    print("InsightFace Model Setup")
    print("=" * 60)

    try:
        from insightface.app import FaceAnalysis
        print("✓ InsightFace package installed")
    except ImportError:
        print("✗ InsightFace not installed. Run: pip install insightface")
        sys.exit(1)

    try:
        import onnxruntime
        print(f"✓ ONNX Runtime installed (version {onnxruntime.__version__})")

        # Check available providers
        providers = onnxruntime.get_available_providers()
        print(f"  Available providers: {providers}")

        if 'CUDAExecutionProvider' in providers:
            print("  ✓ GPU acceleration available")
        else:
            print("  ⚠ GPU not available, using CPU (slower)")
    except ImportError:
        print("✗ ONNX Runtime not installed")
        sys.exit(1)

    print("\nDownloading buffalo_l model (this may take a few minutes)...")

    try:
        # Initialize FaceAnalysis - this downloads the model
        app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider']  # Start with CPU for download
        )

        # Prepare the model
        app.prepare(ctx_id=0, det_size=(640, 640))

        print("✓ Model downloaded and prepared successfully")

        # Verify model works with a test
        print("\nRunning verification test...")

        import numpy as np
        import cv2

        # Create a simple test image (black image with white rectangle as face proxy)
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Try to detect (won't find faces in black image, but verifies model works)
        faces = app.get(test_img)
        print(f"✓ Model inference working (detected {len(faces)} faces in test image)")

        # Get model path
        model_root = os.path.expanduser('~/.insightface/models')
        print(f"\nModel location: {model_root}")

        if os.path.exists(model_root):
            models = os.listdir(model_root)
            print(f"Available models: {models}")

        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nTo use InsightFace in production:")
        print("1. Set FACE_RECOGNITION_MOCK=false in .env")
        print("2. For GPU acceleration, install onnxruntime-gpu:")
        print("   pip install onnxruntime-gpu")
        print("3. Restart the API server")

        return True

    except Exception as e:
        print(f"✗ Error during setup: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you have enough disk space (~500MB)")
        print("2. Check internet connection")
        print("3. Try running with sudo if permission denied")
        return False


def verify_installation():
    """Verify InsightFace is properly installed and working."""
    print("\nVerifying InsightFace installation...")

    try:
        from insightface.app import FaceAnalysis
        import numpy as np
        import cv2

        # Quick test with buffalo_l
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))

        # Create test image with synthetic face-like pattern
        test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        faces = app.get(test_img)

        print(f"✓ InsightFace is working correctly")
        print(f"  Detected {len(faces)} faces in random noise image")
        return True

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Setup InsightFace model')
    parser.add_argument('--verify-only', action='store_true',
                        help='Only verify existing installation')
    args = parser.parse_args()

    if args.verify_only:
        success = verify_installation()
    else:
        success = setup_insightface()

    sys.exit(0 if success else 1)
