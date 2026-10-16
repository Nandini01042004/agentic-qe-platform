"""Enterprise Command Line Interface (CLI) for QualiAgent."""

import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from qualiagent.agents.orchestrator import QEOrchestrator
from qualiagent.agents.analyzer import CodebaseAnalyzerAgent
from qualiagent.core.state import QEPipelineOutput

console = Console()


@click.group()
def cli():
    """QualiAgent: Enterprise Autonomous Quality Engineering (Agentic QE) CLI."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--guidelines", "-g", default="examples/test_guidelines/enterprise_testing_rules.md", help="Path to testing guidelines")
@click.option("--output-test", "-o", default=None, help="Output path to save the generated test file")
def run(file_path: str, guidelines: str, output_test: str):
    """Run full end-to-end Multi-Agent QE pipeline on a Python file."""
    source_path = Path(file_path)
    source_code = source_path.read_text(encoding="utf-8")
    module_name = source_path.stem

    console.print(Panel.fit(
        f"[bold cyan]QualiAgent Enterprise QE Engine[/bold cyan]\n"
        f"Target: [green]{file_path}[/green] | Module: [yellow]{module_name}[/yellow]",
        border_style="cyan"
    ))

    orchestrator = QEOrchestrator(guidelines_path=guidelines)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Running Multi-Agent QE Pipeline...", total=None)
        pipeline_output: QEPipelineOutput = orchestrator.run_pipeline(
            source_code=source_code,
            file_path=file_path,
            module_name=module_name,
        )

    _display_summary(pipeline_output)

    if output_test:
        out_p = Path(output_test)
        out_p.write_text(pipeline_output.final_test_suite.code, encoding="utf-8")
        console.print(f"[bold green]✓ Final test suite written to:[/bold green] {output_test}")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def analyze(file_path: str):
    """Inspect AST interface, cyclomatic complexity, and risk hotspots."""
    source_path = Path(file_path)
    source_code = source_path.read_text(encoding="utf-8")

    analyzer = CodebaseAnalyzerAgent()
    analysis, trace = analyzer.analyze(source_code, file_path=file_path)

    table = Table(title=f"AST Analysis: {file_path}", box=box.ROUNDED)
    table.add_column("Type", style="cyan")
    table.add_column("Identifier", style="bold green")
    table.add_column("Complexity / Signature", style="magenta")
    table.add_column("Exceptions / Info", style="yellow")

    for cls in analysis.classes:
        table.add_row(
            "Class",
            cls.name,
            f"Methods: {len(cls.methods)}",
            cls.docstring[:40] if cls.docstring else "No docstring",
        )
        for m in cls.methods:
            table.add_row(
                "  Method",
                f"{cls.name}.{m.name}",
                f"Complexity: {m.cyclomatic_complexity}",
                f"Raises: {', '.join(m.raised_exceptions) if m.raised_exceptions else 'None'}",
            )

    for fn in analysis.functions:
        table.add_row(
            "Function",
            fn.name,
            f"Complexity: {fn.cyclomatic_complexity}",
            f"Raises: {', '.join(fn.raised_exceptions) if fn.raised_exceptions else 'None'}",
        )

    console.print(table)

    if analysis.detected_risks:
        console.print("\n[bold red]Detected Risk Hotspots:[/bold red]")
        for risk in analysis.detected_risks:
            console.print(f"  [red]• {risk}[/red]")


@cli.command()
@click.pass_context
def demo(ctx: click.Context):
    """Run an instant live demo on the included Enterprise AuthService."""
    sample_path = "examples/sample_code/auth_service.py"
    console.print("[bold yellow]Launching QualiAgent Demo on AuthService...[/bold yellow]")
    ctx.invoke(run, file_path=sample_path, guidelines="examples/test_guidelines/enterprise_testing_rules.md", output_test=None)


def _display_summary(output: QEPipelineOutput):
    """Prints rich formatted summary of the multi-agent results."""
    score = output.scorecard.metrics.overall_qe_score
    grade = output.scorecard.metrics.grade
    color = "green" if grade in ("A+", "A") else ("yellow" if grade == "B" else "red")

    # Scorecard Panel
    score_panel = Panel(
        f"[bold]Quality Engineering Score:[/bold] [{color}]{score}/100 (Grade: {grade})[/{color}]\n"
        f"• Executability Rate: [bold cyan]{output.scorecard.metrics.executability_score}%[/bold cyan]\n"
        f"• Assertion Density: [bold cyan]{output.scorecard.metrics.assertion_density}[/bold cyan] assertions/test\n"
        f"• Estimated Coverage: [bold cyan]{output.scorecard.metrics.estimated_coverage_pct}%[/bold cyan]\n"
        f"• Edge Case Coverage: [bold cyan]{output.scorecard.metrics.edge_case_coverage_score}/10[/bold cyan]\n"
        f"• Mocking Faithfulness: [bold cyan]{output.scorecard.metrics.mocking_faithfulness_score}/10[/bold cyan]\n"
        f"• Hallucination Penalty: [bold red]-{output.scorecard.metrics.hallucination_penalty}[/bold red]",
        title="[bold blue]Enterprise Quality Scorecard[/bold blue]",
        box=box.ROUNDED,
    )
    console.print(score_panel)

    # Test Execution Summary
    exec_res = output.final_execution
    res_table = Table(title="Sandbox Pytest Execution", box=box.ROUNDED)
    res_table.add_column("Metric", style="cyan")
    res_table.add_column("Value", style="bold")
    res_table.add_row("Total Tests", str(exec_res.total_tests))
    res_table.add_row("Passed", f"[green]{exec_res.passed}[/green]")
    res_table.add_row("Failed", f"[red]{exec_res.failed}[/red]")
    res_table.add_row("Duration", f"{exec_res.duration_seconds}s")
    res_table.add_row("Self-Healing Iterations", str(len(output.healing_history)))
    console.print(res_table)

    # Agent Traces Table
    trace_table = Table(title="Multi-Agent Execution Audit Trace", box=box.ROUNDED)
    trace_table.add_column("Agent", style="cyan")
    trace_table.add_column("Role", style="magenta")
    trace_table.add_column("Action", style="green")
    trace_table.add_column("Latency", style="yellow")
    for tr in output.agent_traces:
        trace_table.add_row(tr.agent_name, tr.role, tr.action, f"{tr.latency_ms}ms")
    console.print(trace_table)


if __name__ == "__main__":
    cli()
