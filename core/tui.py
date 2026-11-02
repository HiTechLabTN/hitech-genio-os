#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.engine import GenioEngine, AGENTS_REGISTRY


console = Console()




async def main():
    engine = GenioEngine()
    while True:
        console.clear()
        tel = engine.get_system_telemetry()
        ollama = await engine.check_ollama_status()
        status_str = f"[bold green]ONLINE ({len(ollama['models'])} models)[/]" if ollama["online"] else "[bold red]OFFLINE[/]"


        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="right")
        header.add_row(
            "[bold cyan]⚡ GENIO OS v3.0 — Terminal & Mobile SSH Console[/]",
            f"Node: [bold yellow]{tel['node']}[/] | RAM: {tel['ram_used_gb']}/{tel['ram_total_gb']}GB | /data Free: {tel['disk_free_gb']}GB"
        )
        header.add_row(
            f"Ollama ({tel['ollama_host']}): {status_str}",
            f"Active Model: [bold magenta]{tel['active_model']}[/]"
        )
        console.print(Panel(header, border_style="cyan"))


        t = Table(title="👥 الوكلاء المتاحون (Autonomous Agents)", border_style="blue")
        t.add_column("#", style="cyan", justify="center")
        t.add_column("Agent ID", style="bold white")
        t.add_column("Role", style="green")
        agent_keys = list(AGENTS_REGISTRY.keys())
        for idx, k in enumerate(agent_keys, 1):
            t.add_row(str(idx), f"{AGENTS_REGISTRY[k]['icon']} {k}", AGENTS_REGISTRY[k]["title"])
        console.print(t)


        console.print("\n[bold yellow]الأوامر السريعة:[/] [cyan]1-5[/] لاختيار وكيل وإرسال مهمة | [cyan]f[/] لعرض ملفات /data | [cyan]c[/] لتغيير رابط Ollama/الموديل | [cyan]q[/] للخروج")
        choice = Prompt.ask("👉 اختر رقم الوكيل أو الأمر", default="1")


        if choice.lower() == "q":
            break
        elif choice.lower() == "f":
            files = engine.list_workspace_files()
            console.print(Panel("\n".join([f"📄 {f['path']} ({f['size_kb']} KB)" for f in files]) or "المجلد فارغ", title="ملفات /data/genio-os/workspace"))
            Prompt.ask("اضغط Enter للمتابعة")
        elif choice.lower() == "c":
            new_host = Prompt.ask("رابط Ollama", default=tel["ollama_host"])
            new_model = Prompt.ask("اسم الموديل", default=tel["active_model"])
            engine.save_config({"ollama_host": new_host, "primary_model": new_model})
        elif choice.isdigit() and 1 <= int(choice) <= len(agent_keys):
            ag_id = agent_keys[int(choice) - 1]
            task = Prompt.ask(f"📝 اكتب مهمتك لـ [bold cyan]{ag_id}[/]")
            if task.strip():
                with console.status(f"[bold yellow]⏳ {ag_id} يعالج المهمة ويكتب الملفات في /data/genio-os/workspace ...[/]"):
                    res = await engine.dispatch_task(ag_id, task)
                if res.get("ok"):
                    console.print(Panel(res["reply"], title=f"✅ رد {ag_id} ({res['elapsed_sec']}s)", border_style="green"))
                    for act in res.get("actions", []):
                        console.print(f"  [bold green]✔ Action:[/] {act}")
                else:
                    console.print(f"[bold red]❌ {res.get('error')}[/]")
                Prompt.ask("\nاضغط Enter للمتابعة")




if __name__ == "__main__":
    asyncio.run(main())
