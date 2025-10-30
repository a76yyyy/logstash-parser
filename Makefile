.PHONY: help test test-v test-cov test-unit test-integration test-fast clean install lint format

help:
	@echo "Logstash Parser - 可用命令:"
	@echo ""
	@echo "  make install          - 安装依赖"
	@echo "  make test             - 运行所有测试"
	@echo "  make test-v           - 运行测试（详细输出）"
	@echo "  make test-cov         - 运行测试并生成覆盖率报告"
	@echo "  make test-unit        - 只运行单元测试"
	@echo "  make test-integration - 只运行集成测试"
	@echo "  make test-fast        - 快速测试（无覆盖率）"
	@echo "  make lint             - 运行代码检查"
	@echo "  make format           - 格式化代码"
	@echo "  make clean            - 清理临时文件"
	@echo ""

install:
	@echo "安装依赖..."
	uv sync --group test --group dev

test:
	@echo "运行所有测试..."
	uv run pytest tests/ --cov --cov-report=term-missing

test-v:
	@echo "运行测试（详细输出）..."
	uv run pytest tests/ -v --cov --cov-report=term-missing

test-cov:
	@echo "运行测试并生成 HTML 覆盖率报告..."
	uv run pytest tests/ --cov --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "覆盖率报告已生成: htmlcov/index.html"

test-unit:
	@echo "运行单元测试..."
	uv run pytest tests/ -m unit -v

test-integration:
	@echo "运行集成测试..."
	uv run pytest tests/ -m integration -v

test-fast:
	@echo "快速测试（无覆盖率）..."
	uv run pytest tests/ -v

test-parallel:
	@echo "并行运行测试..."
	uv run pytest tests/ -n auto --cov

lint:
	@echo "运行代码检查..."
	@echo "1. Ruff 检查..."
	uv run ruff check src/logstash_parser tests/
	@echo ""
	@echo "2. Mypy 类型检查..."
	uv run mypy src/logstash_parser

format:
	@echo "格式化代码..."
	uv run ruff format src/logstash_parser tests/
	uv run ruff check --fix src/logstash_parser tests/

clean:
	@echo "清理临时文件..."
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "清理完成！"

.DEFAULT_GOAL := help
