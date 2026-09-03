"""红线测试 T15-9 - 财务独立性：FIN 域不直接依赖 PUR/SAL 域。

验证 EITP-FIN-001 的财务独立性红线：
- FIN domain 层不导入 app.domain.pur / app.domain.sal
- FIN interfaces 层不导入 app.domain.pur / app.domain.sal
- 唯一允许的跨域访问是 infrastructure.fin 中的只读视图
- 只读视图通过 SQL 查询，不导入 PUR/SAL 聚合根
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

# 项目根目录
BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = BACKEND_ROOT / "app"

# 需要检查的 FIN 目录（domain + interfaces）
FIN_CHECK_DIRS = [
    APP_ROOT / "domain" / "fin",
    APP_ROOT / "interfaces" / "api" / "v1" / "fin",
]

# 禁止导入的模块前缀
FORBIDDEN_IMPORT_PREFIXES = ("app.domain.pur", "app.domain.sal")

# 允许的跨域引用（infrastructure 层只读视图）
ALLOWED_CROSS_DOMAIN_MODULES = {
    "app.infrastructure.fin.pur_order_read_view",
    "app.infrastructure.fin.sal_order_read_view",
}


def _collect_python_files(dirs: list[Path]) -> list[Path]:
    """递归收集目录下所有 .py 文件。"""
    result: list[Path] = []
    for d in dirs:
        if not d.exists():
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if f.endswith(".py"):
                    result.append(Path(root) / f)
    return result


def _extract_imports(filepath: Path) -> list[str]:
    """用 AST 提取文件中所有 import 的模块名。"""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _has_forbidden_import(filepath: Path) -> tuple[bool, list[str]]:
    """检查文件是否包含禁止的导入。"""
    imports = _extract_imports(filepath)
    forbidden = [
        imp for imp in imports
        if any(imp.startswith(prefix) for prefix in FORBIDDEN_IMPORT_PREFIXES)
    ]
    return (len(forbidden) > 0, forbidden)


class TestFinanceIndependence:
    """红线 3：FIN 域不直接依赖 PUR/SAL 域。"""

    def test_fin_domain_does_not_import_pur_sal(self) -> None:
        files = _collect_python_files([APP_ROOT / "domain" / "fin"])
        assert len(files) > 0, "FIN domain 目录应有 .py 文件"

        violations: list[str] = []
        for f in files:
            has_forbidden, forbidden = _has_forbidden_import(f)
            if has_forbidden:
                violations.append(f"{f}: {forbidden}")

        assert violations == [], (
            "FIN domain 层禁止直接导入 PUR/SAL 域模块:\n" + "\n".join(violations)
        )

    def test_fin_interfaces_does_not_import_pur_sal(self) -> None:
        files = _collect_python_files([APP_ROOT / "interfaces" / "api" / "v1" / "fin"])
        assert len(files) > 0, "FIN interfaces 目录应有 .py 文件"

        violations: list[str] = []
        for f in files:
            has_forbidden, forbidden = _has_forbidden_import(f)
            if has_forbidden:
                violations.append(f"{f}: {forbidden}")

        assert violations == [], (
            "FIN interfaces 层禁止直接导入 PUR/SAL 域模块:\n" + "\n".join(violations)
        )

    def test_fin_aggregates_do_not_import_pur_sal(self) -> None:
        agg_dir = APP_ROOT / "domain" / "fin" / "aggregates"
        files = _collect_python_files([agg_dir])
        assert len(files) > 0

        for f in files:
            has_forbidden, forbidden = _has_forbidden_import(f)
            assert not has_forbidden, f"{f} 禁止导入 PUR/SAL: {forbidden}"

    def test_fin_value_objects_do_not_import_pur_sal(self) -> None:
        vo_dir = APP_ROOT / "domain" / "fin" / "value_objects"
        files = _collect_python_files([vo_dir])
        assert len(files) > 0

        for f in files:
            has_forbidden, forbidden = _has_forbidden_import(f)
            assert not has_forbidden, f"{f} 禁止导入 PUR/SAL: {forbidden}"

    def test_fin_error_codes_do_not_import_pur_sal(self) -> None:
        filepath = APP_ROOT / "domain" / "fin" / "error_codes.py"
        has_forbidden, forbidden = _has_forbidden_import(filepath)
        assert not has_forbidden, f"error_codes.py 禁止导入 PUR/SAL: {forbidden}"

    def test_fin_exceptions_do_not_import_pur_sal(self) -> None:
        filepath = APP_ROOT / "domain" / "fin" / "exceptions.py"
        has_forbidden, forbidden = _has_forbidden_import(filepath)
        assert not has_forbidden, f"exceptions.py 禁止导入 PUR/SAL: {forbidden}"


class TestReadViewIsolation:
    """红线 3：跨域引用仅通过 infrastructure 只读视图。"""

    def test_read_views_in_infrastructure_not_domain(self) -> None:
        from app.infrastructure.fin.pur_order_read_view import PurOrderReadView
        from app.infrastructure.fin.sal_order_read_view import SalOrderReadView

        assert "infrastructure" in PurOrderReadView.__module__
        assert "infrastructure" in SalOrderReadView.__module__
        assert "domain" not in PurOrderReadView.__module__
        assert "domain" not in SalOrderReadView.__module__

    def test_read_views_do_not_import_pur_sal_aggregates(self) -> None:
        pur_view = APP_ROOT / "infrastructure" / "fin" / "pur_order_read_view.py"
        sal_view = APP_ROOT / "infrastructure" / "fin" / "sal_order_read_view.py"

        for f in [pur_view, sal_view]:
            imports = _extract_imports(f)
            for imp in imports:
                assert not imp.startswith("app.domain.pur"), f"{f} 不应导入 pur domain"
                assert not imp.startswith("app.domain.sal"), f"{f} 不应导入 sal domain"

    def test_read_views_use_sql_not_orm(self) -> None:
        """只读视图通过 SQL text 查询，不通过 ORM session.get/query。"""
        pur_view = APP_ROOT / "infrastructure" / "fin" / "pur_order_read_view.py"
        sal_view = APP_ROOT / "infrastructure" / "fin" / "sal_order_read_view.py"

        for f in [pur_view, sal_view]:
            source = f.read_text(encoding="utf-8")
            assert "text(" in source, f"{f} 应使用 sqlalchemy text() 原始 SQL"


class TestFinSelfContained:
    """红线 3：FIN 域自包含性验证。"""

    def test_fin_error_codes_self_contained(self) -> None:
        """error_codes.py 仅依赖标准库。"""
        filepath = APP_ROOT / "domain" / "fin" / "error_codes.py"
        imports = _extract_imports(filepath)
        for imp in imports:
            assert not imp.startswith("app.domain.pur"), "error_codes 不应依赖 PUR"
            assert not imp.startswith("app.domain.sal"), "error_codes 不应依赖 SAL"

    def test_fin_exceptions_self_contained(self) -> None:
        """exceptions.py 仅依赖 fin.error_codes。"""
        filepath = APP_ROOT / "domain" / "fin" / "exceptions.py"
        imports = _extract_imports(filepath)
        domain_imports = [i for i in imports if i.startswith("app.domain.")]
        for imp in domain_imports:
            assert imp.startswith("app.domain.fin"), (
                f"exceptions.py 仅应依赖 app.domain.fin，实际: {imp}"
            )

    def test_fin_money_self_contained(self) -> None:
        """money.py 仅依赖 fin.error_codes / fin.exceptions。"""
        filepath = APP_ROOT / "domain" / "fin" / "value_objects" / "money.py"
        imports = _extract_imports(filepath)
        domain_imports = [i for i in imports if i.startswith("app.domain.")]
        for imp in domain_imports:
            assert imp.startswith("app.domain.fin"), (
                f"money.py 仅应依赖 app.domain.fin，实际: {imp}"
            )

    def test_fin_enums_self_contained(self) -> None:
        """enums.py 不依赖任何 app 模块。"""
        filepath = APP_ROOT / "domain" / "fin" / "value_objects" / "enums.py"
        imports = _extract_imports(filepath)
        app_imports = [i for i in imports if i.startswith("app.")]
        assert app_imports == [], f"enums.py 不应依赖任何 app 模块: {app_imports}"