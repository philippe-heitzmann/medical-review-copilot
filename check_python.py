#!/usr/bin/env python3
"""
Python Version Compatibility Checker for Medical Literature Review System
"""

import sys
import platform
import subprocess

def check_python_version():
    """Check Python version compatibility"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print("Python Version Compatibility Check")
    print("="*40)
    print(f"Current Python version: {version_str}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print()

    # Check version compatibility
    if version.major != 3:
        print("❌ ERROR: Python 3 is required")
        print(f"   Found: Python {version.major}")
        print("   Please install Python 3.8-3.12")
        return False

    if version.minor < 8:
        print("❌ ERROR: Python 3.8 or higher is required")
        print(f"   Found: Python {version_str}")
        print("   Please upgrade to Python 3.8-3.12")
        return False

    if version.minor <= 12:
        print("✅ COMPATIBLE: Full AI/ML features available")
        print(f"   Python {version_str} supports all components")
        components = {
            "Weekly Triage Workflow": "✅ Full support",
            "Therapeutic Area Copilot": "✅ Full support with AI features",
            "Semantic Search": "✅ Available",
            "Advanced NLP": "✅ Available",
            "Vector Embeddings": "✅ Available"
        }
    elif version.minor == 13:
        print("⚠️  LIMITED COMPATIBILITY: Basic features available")
        print(f"   Python {version_str} has limited ML library support")
        components = {
            "Weekly Triage Workflow": "✅ Full support",
            "Therapeutic Area Copilot": "⚠️  Basic features only",
            "Semantic Search": "⚠️  Keyword search fallback",
            "Advanced NLP": "❌ Not available",
            "Vector Embeddings": "❌ Not available"
        }
    else:
        print("⚠️  EXPERIMENTAL: Very limited compatibility")
        print(f"   Python {version_str} is very new - limited library support")
        components = {
            "Weekly Triage Workflow": "⚠️  May work",
            "Therapeutic Area Copilot": "⚠️  Basic features only",
            "Semantic Search": "⚠️  Keyword search fallback",
            "Advanced NLP": "❌ Not available",
            "Vector Embeddings": "❌ Not available"
        }

    print()
    print("Component Compatibility:")
    print("-" * 40)
    for component, status in components.items():
        print(f"{component:25}: {status}")

    print()

    # Recommendations
    if version.minor > 12:
        print("🔧 RECOMMENDATIONS:")
        print("   For best compatibility, use Python 3.8-3.12")
        print("   Consider using pyenv to manage multiple Python versions:")
        print("   1. Install pyenv: brew install pyenv (macOS) or follow pyenv docs")
        print("   2. Install Python 3.11: pyenv install 3.11.7")
        print("   3. Set local version: pyenv local 3.11.7")
        print()

    # Check available packages
    print("Checking installed packages:")
    print("-" * 40)

    packages_to_check = [
        ('requests', 'Core HTTP client'),
        ('pandas', 'Data processing'),
        ('numpy', 'Numerical computing'),
        ('sentence_transformers', 'AI embeddings'),
        ('torch', 'ML framework'),
        ('transformers', 'NLP models'),
        ('faiss', 'Vector search'),
        ('spacy', 'Advanced NLP'),
    ]

    for package, description in packages_to_check:
        try:
            __import__(package)
            print(f"✅ {package:20}: Available ({description})")
        except ImportError:
            print(f"❌ {package:20}: Not installed ({description})")

    print()
    return True

def main():
    """Main function"""
    compatible = check_python_version()

    if compatible:
        print("🚀 NEXT STEPS:")
        if sys.version_info.minor <= 12:
            print("   Run the setup scripts to install dependencies:")
            print("   ./cleanup_env.sh                    # Clean any previous installs")
            print("   cd weekly-triage-workflow && ./run_triage.sh")
            print("   cd therapeutic-area-copilot && ./run_copilot.sh")
        else:
            print("   You can proceed with limited functionality:")
            print("   ./cleanup_env.sh                    # Clean any previous installs")
            print("   cd weekly-triage-workflow && ./run_triage.sh  # Should work")
            print("   cd therapeutic-area-copilot && ./run_copilot.sh  # Basic features")
    else:
        print("❌ Please install a compatible Python version (3.8-3.12) before proceeding")

    print()

if __name__ == "__main__":
    main()