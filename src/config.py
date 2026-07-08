"""경로·모델 설정. 프로젝트 루트 기준으로 데이터 경로를 절대화한다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "docs"
DB_PATH = ROOT / "data" / "sample.db"

# 최신 모델명으로 .env에서 조정 가능
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
