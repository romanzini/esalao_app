"""
Code Quality and Structure Validation for Phase 3.

This script validates the implementation quality without requiring a running server.
"""

import os
import sys
import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CodeQualityMetric:
    """Metric for code quality assessment."""
    category: str
    metric: str
    value: Any
    target: Any
    passed: bool
    details: str = ""


class Phase3CodeValidator:
    """Validates Phase 3 code quality and implementation."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backend_dir = self.project_root / "backend"
        self.app_dir = self.backend_dir / "app"
        self.metrics: List[CodeQualityMetric] = []

    def validate_file_structure(self) -> List[CodeQualityMetric]:
        """Validate Phase 3 file structure."""
        metrics = []

        # Expected Phase 3 files (actual project structure)
        expected_files = [
            # Policies
            "app/db/models/cancellation_policy.py",
            "app/api/v1/routes/cancellation_policies.py",
            "app/api/v1/schemas/cancellation_policies.py",

            # No-show detection
            "app/services/no_show.py",
            "app/api/v1/routes/no_show_jobs.py",
            "app/api/v1/schemas/no_show.py",

            # Audit events
            "app/db/models/audit_event.py",
            "app/api/v1/routes/audit.py",
            "app/api/v1/schemas/audit.py",

            # Reporting
            "app/api/v1/routes/reports.py",
            "app/api/v1/routes/platform_reports.py",
            "app/api/v1/schemas/reports.py",

            # Performance optimization
            "app/api/v1/routes/optimized_reports.py",

            # Main components
            "app/main.py",
            "app/core/config.py",
            "app/db/session.py",
        ]

        missing_files = []
        existing_files = []

        for file_path in expected_files:
            full_path = self.backend_dir / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)

        metrics.append(CodeQualityMetric(
            category="Structure",
            metric="File Coverage",
            value=f"{len(existing_files)}/{len(expected_files)}",
            target="100%",
            passed=len(missing_files) == 0,
            details=f"Missing: {missing_files}" if missing_files else "All files present"
        ))

        return metrics

    def validate_imports_and_dependencies(self) -> List[CodeQualityMetric]:
        """Validate imports and dependencies."""
        metrics = []

        # Check for proper dependency imports
        required_imports = {
            "fastapi": ["FastAPI", "APIRouter", "Depends", "HTTPException"],
            "sqlalchemy": ["Column", "Integer", "String", "DateTime"],
            "pydantic": ["BaseModel", "Field"],
            "redis": ["Redis"],
        }

        python_files = list(self.app_dir.rglob("*.py"))
        import_coverage = {}

        for package, classes in required_imports.items():
            import_coverage[package] = {"found": 0, "expected": len(classes)}

            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for class_name in classes:
                        if f"from {package}" in content and class_name in content:
                            import_coverage[package]["found"] += 1
                            break

                except Exception:
                    continue

        # Calculate import compliance
        total_expected = sum(data["expected"] for data in import_coverage.values())
        total_found = sum(data["found"] for data in import_coverage.values())

        metrics.append(CodeQualityMetric(
            category="Dependencies",
            metric="Import Coverage",
            value=f"{total_found}/{total_expected}",
            target="80%",
            passed=total_found / total_expected >= 0.8,
            details=f"Import usage: {import_coverage}"
        ))

        return metrics

    def validate_code_patterns(self) -> List[CodeQualityMetric]:
        """Validate code patterns and best practices."""
        metrics = []

        python_files = list(self.app_dir.rglob("*.py"))

        # Pattern checks
        async_functions = 0
        error_handling = 0
        type_hints = 0
        docstrings = 0
        total_functions = 0

        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST for detailed analysis
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                        total_functions += 1

                        # Check for async functions
                        if isinstance(node, ast.AsyncFunctionDef):
                            async_functions += 1

                        # Check for type hints
                        if node.returns or any(arg.annotation for arg in node.args.args):
                            type_hints += 1

                        # Check for docstrings
                        if (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)):
                            docstrings += 1

                        # Check for error handling (try/except blocks)
                        for child in ast.walk(node):
                            if isinstance(child, ast.Try):
                                error_handling += 1
                                break

            except Exception:
                continue

        if total_functions > 0:
            metrics.extend([
                CodeQualityMetric(
                    category="Code Quality",
                    metric="Async Usage",
                    value=f"{async_functions}/{total_functions}",
                    target="50%",
                    passed=async_functions / total_functions >= 0.5,
                    details=f"{(async_functions/total_functions)*100:.1f}% async functions"
                ),
                CodeQualityMetric(
                    category="Code Quality",
                    metric="Type Hints",
                    value=f"{type_hints}/{total_functions}",
                    target="80%",
                    passed=type_hints / total_functions >= 0.8,
                    details=f"{(type_hints/total_functions)*100:.1f}% functions with type hints"
                ),
                CodeQualityMetric(
                    category="Code Quality",
                    metric="Error Handling",
                    value=f"{error_handling}/{total_functions}",
                    target="60%",
                    passed=error_handling / total_functions >= 0.6,
                    details=f"{(error_handling/total_functions)*100:.1f}% functions with error handling"
                ),
                CodeQualityMetric(
                    category="Documentation",
                    metric="Docstring Coverage",
                    value=f"{docstrings}/{total_functions}",
                    target="70%",
                    passed=docstrings / total_functions >= 0.7,
                    details=f"{(docstrings/total_functions)*100:.1f}% functions documented"
                )
            ])

        return metrics

    def validate_phase3_features(self) -> List[CodeQualityMetric]:
        """Validate specific Phase 3 feature implementations."""
        metrics = []

        # Feature implementation checks (updated for actual structure)
        feature_checks = {
            "Cancellation Policies": {
                "files": ["app/db/models/cancellation_policy.py", "app/api/v1/routes/cancellation_policies.py"],
                "patterns": ["class CancellationPolicy", "CancellationPolicyRequest", "CancellationTier"]
            },
            "No-Show Detection": {
                "files": ["app/services/no_show.py", "app/api/v1/routes/no_show_jobs.py"],
                "patterns": ["def process_no_show", "NoShowStatus", "detect_no_show"]
            },
            "Audit System": {
                "files": ["app/db/models/audit_event.py", "app/api/v1/routes/audit.py"],
                "patterns": ["class AuditEvent", "AuditEventType", "EventType"]
            },
            "Reporting System": {
                "files": ["app/api/v1/routes/reports.py", "app/api/v1/routes/platform_reports.py"],
                "patterns": ["BookingMetrics", "RevenueReport", "DashboardData"]
            },
            "Performance Optimization": {
                "files": ["app/api/v1/routes/optimized_reports.py"],
                "patterns": ["cache", "redis", "optimized"]
            }
        }

        for feature_name, config in feature_checks.items():
            patterns_found = 0
            files_found = 0

            for file_path in config["files"]:
                full_path = self.backend_dir / file_path
                if full_path.exists():
                    files_found += 1

                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for pattern in config["patterns"]:
                            if pattern in content:
                                patterns_found += 1
                    except Exception:
                        pass

            total_patterns = len(config["patterns"])
            implementation_score = (patterns_found / total_patterns) if total_patterns > 0 else 0

            metrics.append(CodeQualityMetric(
                category="Features",
                metric=f"{feature_name} Implementation",
                value=f"{patterns_found}/{total_patterns} patterns",
                target="80%",
                passed=implementation_score >= 0.8,
                details=f"Files: {files_found}/{len(config['files'])}, Patterns: {patterns_found}/{total_patterns}"
            ))

        return metrics

    def validate_database_models(self) -> List[CodeQualityMetric]:
        """Validate database model implementations."""
        metrics = []

        model_files = list((self.app_dir / "db" / "models").glob("*.py"))

        models_found = 0
        relationships_found = 0
        indexes_found = 0

        for model_file in model_files:
            if model_file.name == "__init__.py":
                continue

            try:
                with open(model_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for SQLAlchemy models
                if "class " in content and "Base" in content:
                    models_found += 1

                # Check for relationships
                if "relationship(" in content:
                    relationships_found += 1

                # Check for indexes
                if "index=" in content or "Index(" in content:
                    indexes_found += 1

            except Exception:
                continue

        metrics.extend([
            CodeQualityMetric(
                category="Database",
                metric="Model Implementation",
                value=f"{models_found} models",
                target="≥5",
                passed=models_found >= 5,
                details=f"Found {models_found} SQLAlchemy models"
            ),
            CodeQualityMetric(
                category="Database",
                metric="Relationships",
                value=f"{relationships_found} relationships",
                target="≥3",
                passed=relationships_found >= 3,
                details=f"Found {relationships_found} model relationships"
            ),
            CodeQualityMetric(
                category="Database",
                metric="Performance Indexes",
                value=f"{indexes_found} indexed models",
                target="≥2",
                passed=indexes_found >= 2,
                details=f"Found {indexes_found} models with indexes"
            )
        ])

        return metrics

    def validate_api_endpoints(self) -> List[CodeQualityMetric]:
        """Validate API endpoint implementations."""
        metrics = []

        endpoint_files = list((self.app_dir / "api" / "v1" / "routes").glob("*.py"))

        routers_found = 0
        endpoints_found = 0
        response_models_found = 0

        for endpoint_file in endpoint_files:
            if endpoint_file.name == "__init__.py":
                continue

            try:
                with open(endpoint_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for APIRouter
                if "APIRouter" in content:
                    routers_found += 1

                # Count endpoint decorators
                endpoints_found += len(re.findall(r'@router\.(get|post|put|delete|patch)', content))

                # Check for response models
                if "response_model=" in content:
                    response_models_found += 1

            except Exception:
                continue

        metrics.extend([
            CodeQualityMetric(
                category="API",
                metric="Router Implementation",
                value=f"{routers_found} routers",
                target="≥6",
                passed=routers_found >= 6,
                details=f"Found {routers_found} API routers"
            ),
            CodeQualityMetric(
                category="API",
                metric="Endpoint Coverage",
                value=f"{endpoints_found} endpoints",
                target="≥20",
                passed=endpoints_found >= 20,
                details=f"Found {endpoints_found} API endpoints"
            ),
            CodeQualityMetric(
                category="API",
                metric="Response Models",
                value=f"{response_models_found} models",
                target="≥4",
                passed=response_models_found >= 4,
                details=f"Found {response_models_found} files with response models"
            )
        ])

        return metrics

    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete Phase 3 code validation."""
        print("Starting Phase 3 Code Quality Validation...")

        all_metrics = []

        # Run all validation checks
        validation_methods = [
            ("File Structure", self.validate_file_structure),
            ("Dependencies", self.validate_imports_and_dependencies),
            ("Code Patterns", self.validate_code_patterns),
            ("Phase 3 Features", self.validate_phase3_features),
            ("Database Models", self.validate_database_models),
            ("API Endpoints", self.validate_api_endpoints),
        ]

        for validation_name, validation_method in validation_methods:
            print(f"\n{validation_name} Validation:")
            try:
                metrics = validation_method()
                for metric in metrics:
                    status = "✅" if metric.passed else "❌"
                    print(f"  {metric.metric}: {metric.value} ({metric.target}) {status}")
                    if metric.details:
                        print(f"    {metric.details}")

                all_metrics.extend(metrics)

            except Exception as e:
                print(f"  Error in {validation_name} validation: {e}")

        self.metrics = all_metrics
        return self.generate_validation_report()

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        categories = {}
        total_passed = 0
        total_metrics = len(self.metrics)

        # Group metrics by category
        for metric in self.metrics:
            if metric.category not in categories:
                categories[metric.category] = {"metrics": [], "passed": 0, "total": 0}

            categories[metric.category]["metrics"].append(metric)
            categories[metric.category]["total"] += 1

            if metric.passed:
                categories[metric.category]["passed"] += 1
                total_passed += 1

        # Calculate category scores
        for category in categories.values():
            category["score"] = (category["passed"] / category["total"]) * 100 if category["total"] > 0 else 0

        overall_score = (total_passed / total_metrics) * 100 if total_metrics > 0 else 0

        report = {
            "validation_summary": {
                "total_metrics": total_metrics,
                "passed_metrics": total_passed,
                "overall_score": overall_score,
                "grade": self._calculate_grade(overall_score),
                "timestamp": datetime.now().isoformat()
            },
            "category_scores": {
                cat_name: {
                    "score": cat_data["score"],
                    "passed": cat_data["passed"],
                    "total": cat_data["total"]
                }
                for cat_name, cat_data in categories.items()
            },
            "detailed_metrics": [
                {
                    "category": m.category,
                    "metric": m.metric,
                    "value": str(m.value),
                    "target": str(m.target),
                    "passed": m.passed,
                    "details": m.details
                }
                for m in self.metrics
            ],
            "recommendations": self._generate_recommendations(categories)
        }

        return report

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade based on score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self, categories: Dict) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        for cat_name, cat_data in categories.items():
            if cat_data["score"] < 80:
                failed_metrics = [m for m in cat_data["metrics"] if not m.passed]
                if failed_metrics:
                    rec = f"Improve {cat_name}: {len(failed_metrics)} metrics need attention"
                    recommendations.append(rec)

        if not recommendations:
            recommendations.append("Excellent code quality! All metrics are meeting targets.")

        return recommendations


def main():
    """Main function to run code validation."""
    validator = Phase3CodeValidator()

    try:
        # Run validation
        report = validator.run_full_validation()

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"phase3_validation_report_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        print("\n" + "="*60)
        print("PHASE 3 CODE QUALITY VALIDATION SUMMARY")
        print("="*60)

        summary = report["validation_summary"]
        categories = report["category_scores"]

        print(f"Overall Score: {summary['overall_score']:.1f}% (Grade: {summary['grade']})")
        print(f"Metrics Passed: {summary['passed_metrics']}/{summary['total_metrics']}")

        print("\nCategory Breakdown:")
        for cat_name, cat_data in categories.items():
            score = cat_data["score"]
            status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            print(f"  {cat_name}: {score:.1f}% ({cat_data['passed']}/{cat_data['total']}) {status}")

        print("\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")

        print(f"\nDetailed report saved to: {report_file}")

        return report

    except Exception as e:
        print(f"Code validation failed: {e}")
        return None


if __name__ == "__main__":
    main()
