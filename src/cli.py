"""MCP 클라이언트 없이 파이프라인을 바로 테스트하는 CLI.

    python -m src.cli "송도 C현장 3층 진척률 몇 %야?"
"""
import sys

from .graph import run_pipeline


def main():
    question = " ".join(sys.argv[1:]).strip() or input("질문: ").strip()
    if not question:
        print("질문을 입력하세요.")
        return
    print(run_pipeline(question))


if __name__ == "__main__":
    main()
