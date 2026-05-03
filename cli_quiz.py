import os
import re
import json
import glob
import random
import sys
from datetime import datetime

# Ensure unicode block characters render on Windows consoles using legacy code pages.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.align import Align
    from rich.table import Table
    from rich.columns import Columns
    from rich.padding import Padding
    from rich.rule import Rule
    from rich.box import ROUNDED, MINIMAL, SIMPLE
    import questionary
    from questionary import Style as QStyle
except ImportError:
    print("缺少必要的套件。請先在終端機執行以下指令安裝：")
    print("pip install rich questionary")
    sys.exit(1)

console = Console()

# ───────────── Theme ─────────────
APP_NAME    = "iPAS"
APP_TAGLINE = "AI Application Planner · Practice Console"
APP_VERSION = "v1.1"

C_PRIMARY = "bright_cyan"
C_ACCENT  = "cyan"
C_SUCCESS = "bright_green"
C_ERROR   = "bright_red"
C_WARN    = "yellow"
C_MUTED   = "bright_black"
C_TEXT    = "white"

# prompt-toolkit colour names (questionary uses prompt-toolkit, which expects ansi*-style names)
PT_PRIMARY = "ansibrightcyan"
PT_ACCENT  = "ansicyan"
PT_SUCCESS = "ansibrightgreen"
PT_ERROR   = "ansibrightred"
PT_WARN    = "ansiyellow"
PT_MUTED   = "ansibrightblack"

Q_STYLE = QStyle([
    ('qmark',       f'fg:{PT_ACCENT} bold'),
    ('question',    'bold'),
    ('answer',      f'fg:{PT_SUCCESS} bold'),
    ('pointer',     f'fg:{PT_ACCENT} bold'),
    ('highlighted', f'fg:{PT_ACCENT} bold'),
    ('selected',    f'fg:{PT_SUCCESS}'),
    ('separator',   f'fg:{PT_MUTED}'),
    ('instruction', f'fg:{PT_MUTED}'),
    ('text',        ''),
    ('disabled',    f'fg:{PT_MUTED} italic'),
])


# ───────────── Utilities ─────────────
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def normalize_text(text):
    return text.translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))


def get_category_from_filename(filename):
    if "人工智慧基礎概論" in filename:
        return "人工智慧基礎概論"
    elif "生成式AI應用與規劃" in filename:
        return "生成式AI應用與規劃"
    return "其他"


def map_option(opt):
    mapping = {'A': '1', 'B': '2', 'C': '3', 'D': '4'}
    return mapping.get(opt.upper(), opt.upper())


def truncate(text, width):
    text = text.replace('\n', ' ')
    return text if len(text) <= width else text[:width - 1] + "…"


# ───────────── Parsing ─────────────
def parse_files(directory):
    questions = []
    re_question_start = re.compile(r'^([A-Da-d])\s+(\d+)\.\s+(.*)')
    re_option = re.compile(r'^[\(（]?([A-Da-d])[\)）\.\、]\s*(.*)')
    re_ignore = re.compile(r'^(===|11[45]\s*年|第一科|第二科|考試日期|第\s*\d+\s*頁|答案\s*題\s*目|一、選擇題)')

    for filepath in glob.glob(os.path.join(directory, '*.txt')):
        filename = os.path.basename(filepath)
        category = get_category_from_filename(filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_q = None
        for line in lines:
            line = line.strip()
            if not line or re_ignore.search(line):
                continue

            norm_line = normalize_text(line)

            q_match = re_question_start.match(norm_line)
            if q_match:
                if current_q and current_q.get('options'):
                    questions.append(current_q)

                current_q = {
                    'id': f"{filename}_{q_match.group(2)}",
                    'category': category,
                    'source': filename,
                    'number': q_match.group(2),
                    'answer': map_option(q_match.group(1)),
                    'question': q_match.group(3).strip(),
                    'options': {}
                }
                continue

            opt_match = re_option.match(norm_line)
            if opt_match and current_q:
                opt_key = map_option(opt_match.group(1))
                opt_text = opt_match.group(2).strip().rstrip('；')
                current_q['options'][opt_key] = opt_text
                continue

            if current_q:
                if not current_q['options']:
                    current_q['question'] += '\n' + line
                else:
                    last_opt = list(current_q['options'].keys())[-1]
                    current_q['options'][last_opt] += '\n' + line.rstrip('；')

        if current_q and current_q.get('options'):
            questions.append(current_q)

    return questions


def load_wrong_questions(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_wrong_questions(filepath, wrong_dict):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(wrong_dict, f, ensure_ascii=False, indent=2)


def _match_key(text):
    """Normalize text for fuzzy substring matching: fullwidth → ASCII, strip all whitespace."""
    return re.sub(r'\s+', '', normalize_text(text))


def _extract_question_text(block):
    """Pull the question stem from an explanation block (handles both markdown formats)."""
    # Format B (錯題記錄): **情境**：xxx
    ctx = re.search(r'\*\*情境\*\*\s*[：:]\s*([^\n]+)', block)
    if ctx:
        return ctx.group(1).strip()
    # Format A (全攻略): first bold paragraph that looks like a real sentence
    for m in re.finditer(r'\*\*([^\*\n]{15,})\*\*', block):
        candidate = m.group(1).strip()
        # Skip section markers like 解析 / 破題攻略 / 你的答案
        if any(skip in candidate for skip in ('解析', '破題攻略', '正確答案', '你的答案', '錯誤答案')):
            continue
        return candidate
    return None


def load_explanations(*filepaths):
    """Load explanations from one or more markdown files. Returns dict[key] = (analysis, strategy)."""
    explanations = {}

    re_analysis = re.compile(
        r'\*\*\s*(?:🔍\s*)?解析\s*\*\*\s*[：:]?\s*\n?(.*?)'
        r'(?=\n\s*\*\*\s*(?:💡|🎯|📌)?\s*破題攻略\s*\*\*|\n\s*---|\n\s*###|\Z)',
        re.DOTALL
    )
    re_strategy = re.compile(
        r'\*\*\s*(?:💡|🎯|📌)?\s*破題攻略\s*\*\*\s*[：:]?\s*\n?(.*?)'
        r'(?=\n\s*---|\n\s*###|\Z)',
        re.DOTALL
    )

    for filepath in filepaths:
        if not filepath or not os.path.exists(filepath):
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        blocks = re.split(r'^###\s+Q[^\n]*\n', content, flags=re.MULTILINE)
        for block in blocks[1:]:
            question_text = _extract_question_text(block)
            if not question_text:
                continue

            # Shorter key (22 chars) tolerates the summarised wording in the
            # comprehensive guide vs. the verbose original on the exam paper.
            key = _match_key(question_text)[:22]
            if len(key) < 10:
                continue

            analysis = re_analysis.search(block)
            strategy = re_strategy.search(block)
            payload = (
                analysis.group(1).strip() if analysis else None,
                strategy.group(1).strip() if strategy else None,
            )
            if not (payload[0] or payload[1]):
                continue

            # Prefer the first occurrence (don't let later, sparser entries overwrite richer ones)
            explanations.setdefault(key, payload)

    return explanations


def lookup_explanation(explanations, question_text):
    """Find the (analysis, strategy) tuple whose key is a substring of the normalized question."""
    haystack = _match_key(question_text)
    for key, payload in explanations.items():
        if key in haystack:
            return payload
    return None


# ───────────── UI Components ─────────────
def render_topbar():
    """Compact branded header bar."""
    width = console.size.width
    left = Text()
    left.append(f" {APP_NAME} ", style=f"bold black on {C_PRIMARY}")
    left.append(f"  {APP_TAGLINE}", style=f"bold {C_TEXT}")

    right = Text(f"{APP_VERSION}  {datetime.now().strftime('%Y-%m-%d %H:%M')} ", style=C_MUTED)

    pad = max(1, width - len(left.plain) - len(right.plain))
    bar = Text.assemble(left, " " * pad, right)
    console.print(bar)
    console.print(Rule(style=C_MUTED))


def render_footer(hints):
    """Bottom hint bar — keybinding cheatsheet."""
    parts = []
    for i, (key, label) in enumerate(hints):
        if i > 0:
            parts.append(("  ·  ", C_MUTED))
        parts.append((f" {key} ", f"bold black on {C_ACCENT}"))
        parts.append((f" {label}", C_MUTED))
    text = Text()
    for content, style in parts:
        text.append(content, style=style)
    console.print(Rule(style=C_MUTED))
    console.print(text)


def render_screen_header(title, subtitle=None):
    """Section title block."""
    title_text = Text(f"  {title}", style=f"bold {C_PRIMARY}")
    console.print()
    console.print(title_text)
    if subtitle:
        console.print(Text(f"  {subtitle}", style=C_MUTED))
    console.print()


def stat_chip(label, value, color):
    """Small inline metric — used in progress strip."""
    t = Text()
    t.append(f" {label} ", style=f"{C_MUTED}")
    t.append(f"{value}", style=f"bold {color}")
    return t


def render_progress_strip(idx, total, correct, wrong, mode_label):
    """Live stats bar shown above each question."""
    answered = correct + wrong
    accuracy = (correct / answered * 100) if answered > 0 else 0.0

    # progress bar
    bar_width = 28
    filled = int(bar_width * idx / total) if total > 0 else 0
    bar = Text()
    bar.append("█" * filled, style=C_PRIMARY)
    bar.append("░" * (bar_width - filled), style=C_MUTED)

    line = Text()
    line.append(f" {mode_label} ", style=f"bold black on {C_PRIMARY}")
    line.append("  ")
    line.append_text(bar)
    line.append(f"  {idx}/{total}", style=f"bold {C_TEXT}")
    line.append("    ")
    line.append_text(stat_chip("CORRECT", correct, C_SUCCESS))
    line.append("   ")
    line.append_text(stat_chip("WRONG", wrong, C_ERROR))
    line.append("   ")
    line.append_text(stat_chip("ACCURACY", f"{accuracy:.0f}%", C_WARN))

    console.print(line)
    console.print(Rule(style=C_MUTED))


def render_question_card(q, index_label):
    """The question itself — metadata header + body."""
    meta = Table.grid(padding=(0, 2), expand=True)
    meta.add_column(justify="left", ratio=1)
    meta.add_column(justify="right", ratio=1)

    left = Text()
    left.append("CATEGORY  ", style=f"bold {C_MUTED}")
    left.append(q['category'], style=f"{C_TEXT}")

    right = Text()
    right.append("SOURCE  ", style=f"bold {C_MUTED}")
    right.append(truncate(q['source'].replace('.txt', ''), 50), style=f"{C_TEXT}")

    meta.add_row(left, right)

    body = Text()
    body.append(f"{index_label}  ", style=f"bold {C_ACCENT}")
    body.append(f"#{q['number']}\n\n", style=f"bold {C_MUTED}")
    body.append(q['question'], style=f"{C_TEXT}")

    panel = Panel(
        Group(meta, Rule(style=C_MUTED), Padding(body, (1, 1, 0, 1))),
        box=ROUNDED,
        border_style=C_PRIMARY,
        padding=(0, 1),
    )
    console.print(panel)


def render_feedback(is_correct, correct_answer, correct_text):
    """Verdict badge after answering."""
    console.print()
    if is_correct:
        badge = Text("  CORRECT  ", style=f"bold black on {C_SUCCESS}")
        msg = Text("  Nicely done.", style=C_MUTED)
    else:
        badge = Text("  INCORRECT  ", style=f"bold black on {C_ERROR}")
        msg = Text(f"  Answer: ({correct_answer}) {truncate(correct_text, 70)}", style=C_TEXT)
    line = Text.assemble(badge, msg)
    console.print(line)


def render_explanation(payload):
    """Render an (analysis_md, strategy_md) tuple as a panel with proper markdown formatting."""
    analysis, strategy = payload
    parts = []
    if analysis:
        parts.append(Text("ANALYSIS", style=f"bold {C_ACCENT}"))
        parts.append(Markdown(analysis, code_theme="ansi_dark"))
    if strategy:
        if parts:
            parts.append(Text(""))
        parts.append(Text("STRATEGY", style=f"bold {C_WARN}"))
        parts.append(Markdown(strategy, code_theme="ansi_dark"))

    panel = Panel(
        Group(*parts),
        title=f"[bold {C_ACCENT}]Explanation[/]",
        title_align="left",
        border_style=C_ACCENT,
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def render_no_explanation():
    panel = Panel(
        Text("No explanation has been written for this question yet.", style=f"italic {C_MUTED}"),
        title=f"[bold {C_MUTED}]Explanation[/]",
        title_align="left",
        border_style=C_MUTED,
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def render_dashboard(total_q, wrong_q, categories, all_questions, explained_q=0):
    """Main menu summary dashboard — KPI cards + category breakdown."""

    # KPI cards row
    def kpi(label, value, color, hint=None):
        t = Table.grid(padding=(0, 0))
        t.add_column()
        t.add_row(Text(label, style=f"bold {C_MUTED}"))
        t.add_row(Text(str(value), style=f"bold {color}"))
        if hint:
            t.add_row(Text(hint, style=C_MUTED))
        return Panel(t, box=ROUNDED, border_style=C_MUTED, padding=(1, 2))

    coverage_pct = (explained_q / total_q * 100) if total_q else 0
    coverage_color = C_SUCCESS if coverage_pct >= 80 else C_WARN if coverage_pct >= 40 else C_ERROR

    kpis = Columns(
        [
            kpi("TOTAL QUESTIONS", total_q, C_PRIMARY),
            kpi("WRONG ON FILE", wrong_q, C_ERROR if wrong_q else C_MUTED),
            kpi("EXPLAINED", f"{explained_q}/{total_q}", coverage_color, hint=f"{coverage_pct:.0f}% coverage"),
            kpi("CATEGORIES", len(categories), C_ACCENT),
        ],
        expand=True,
        equal=True,
    )
    console.print(kpis)

    # Category breakdown table
    table = Table(
        box=SIMPLE,
        expand=True,
        show_header=True,
        header_style=f"bold {C_MUTED}",
        border_style=C_MUTED,
        padding=(0, 1),
    )
    table.add_column("CATEGORY", style=C_TEXT)
    table.add_column("QUESTIONS", justify="right", style=C_PRIMARY)
    table.add_column("DISTRIBUTION", justify="left")

    for cat in categories:
        count = sum(1 for q in all_questions if q['category'] == cat)
        ratio = count / total_q if total_q else 0
        bar_w = 30
        filled = int(bar_w * ratio)
        bar = Text()
        bar.append("█" * filled, style=C_PRIMARY)
        bar.append("░" * (bar_w - filled), style=C_MUTED)
        bar.append(f"  {ratio * 100:.0f}%", style=C_MUTED)
        table.add_row(cat, str(count), bar)

    console.print()
    console.print(table)


# ───────────── Quiz Engine ─────────────
def run_quiz(quiz_questions, wrong_dict, wrong_file_path, explanations, is_review=False):
    if not quiz_questions:
        clear_screen()
        render_topbar()
        render_screen_header("No questions available", "請先確認 past_exams 目錄下有題庫檔案。")
        input("Enter 返回主選單...")
        return

    quiz_questions = list(quiz_questions)
    random.shuffle(quiz_questions)

    total = len(quiz_questions)
    correct = 0
    wrong = 0
    answered = 0
    aborted = False
    mode_label = "REVIEW MODE" if is_review else "PRACTICE"

    for i, q in enumerate(quiz_questions):
        clear_screen()
        render_topbar()

        render_progress_strip(i + 1, total, correct, wrong, mode_label)
        console.print()
        render_question_card(q, f"Q{i + 1}")

        choices = [
            questionary.Choice(f"({k})  {q['options'][k]}", value=k)
            for k in sorted(q['options'].keys())
        ]
        choices.append(questionary.Separator())
        choices.append(questionary.Choice("End session and view summary", value="Q"))

        console.print()
        user_ans = questionary.select(
            "Select your answer",
            choices=choices,
            use_indicator=False,
            qmark="▸",
            pointer="▸",
            style=Q_STYLE,
            instruction="(↑/↓ navigate · Enter submit)",
        ).ask()

        if user_ans == 'Q' or user_ans is None:
            aborted = True
            break

        answered += 1
        is_correct = (user_ans == q['answer'])
        correct_text = q['options'].get(q['answer'], '')

        render_feedback(is_correct, q['answer'], correct_text)

        if is_correct:
            correct += 1
            if is_review and q['id'] in wrong_dict:
                console.print(Text("  · Removed from wrong-question log.", style=C_MUTED))
                del wrong_dict[q['id']]
                save_wrong_questions(wrong_file_path, wrong_dict)
        else:
            wrong += 1
            if q['id'] not in wrong_dict:
                wrong_dict[q['id']] = q
                save_wrong_questions(wrong_file_path, wrong_dict)
                console.print(Text("  · Logged to wrong-question file for review.", style=C_MUTED))

        # Explanation — always shown in review mode so the user can study every wrong question.
        payload = lookup_explanation(explanations, q['question'])
        if payload:
            render_explanation(payload)
        elif is_review or not is_correct:
            render_no_explanation()

        render_footer([("Enter", "next question"), ("Ctrl+C", "abort")])
        try:
            input()
        except KeyboardInterrupt:
            aborted = True
            break

    render_summary(correct, wrong, answered, total, aborted, mode_label)


def render_summary(correct, wrong, answered, total, aborted, mode_label):
    clear_screen()
    render_topbar()

    accuracy = (correct / answered * 100) if answered > 0 else 0.0
    grade = _grade_for(accuracy) if answered > 0 else ("—", C_MUTED)

    render_screen_header("Session Summary", f"Mode · {mode_label}{' · ABORTED' if aborted else ''}")

    # Stats panel
    stats = Table.grid(padding=(0, 4), expand=True)
    stats.add_column(justify="center", ratio=1)
    stats.add_column(justify="center", ratio=1)
    stats.add_column(justify="center", ratio=1)
    stats.add_column(justify="center", ratio=1)

    def cell(label, value, color):
        t = Table.grid()
        t.add_column(justify="center")
        t.add_row(Text(label, style=f"bold {C_MUTED}"))
        t.add_row(Text(str(value), style=f"bold {color}"))
        return t

    stats.add_row(
        cell("ANSWERED", f"{answered}/{total}", C_PRIMARY),
        cell("CORRECT", correct, C_SUCCESS),
        cell("WRONG", wrong, C_ERROR),
        cell("ACCURACY", f"{accuracy:.1f}%", grade[1]),
    )

    panel = Panel(
        stats,
        title=f"[bold {grade[1]}]GRADE  {grade[0]}[/]",
        title_align="left",
        border_style=grade[1],
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)

    render_footer([("Enter", "back to main menu")])
    input()


def _grade_for(accuracy):
    if accuracy >= 90:
        return ("A · Excellent", C_SUCCESS)
    if accuracy >= 75:
        return ("B · Good", C_PRIMARY)
    if accuracy >= 60:
        return ("C · Pass", C_WARN)
    return ("D · Needs work", C_ERROR)


# ───────────── Main flow ─────────────
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    past_exams_dir = os.path.join(script_dir, 'past_exams')
    wrong_file_path = os.path.join(script_dir, 'wrong_questions', 'wrong_questions.json')

    # Explanations are merged from multiple sources so every question can ideally surface a study note.
    explanation_sources = [
        os.path.join(script_dir, 'iPAS_AI考古題_全攻略.md'),
        os.path.join(script_dir, 'wrong_questions', '錯題記錄_20260429.md'),
    ]

    os.makedirs(os.path.dirname(wrong_file_path), exist_ok=True)

    clear_screen()
    render_topbar()
    with console.status(f"[bold {C_PRIMARY}]Loading question bank and explanations…[/]", spinner="line"):
        all_questions = parse_files(past_exams_dir)
        wrong_dict = load_wrong_questions(wrong_file_path)
        explanations = load_explanations(*explanation_sources)
        categories = sorted(set(q['category'] for q in all_questions))
        covered = sum(1 for q in all_questions if lookup_explanation(explanations, q['question']))

    while True:
        clear_screen()
        render_topbar()
        render_screen_header("Dashboard", "Overview of your question bank and progress")
        render_dashboard(len(all_questions), len(wrong_dict), categories, all_questions, explained_q=covered)

        console.print()
        choices = [
            questionary.Choice("Browse by category    ·  pick a subject and practise", value="1"),
            questionary.Choice("Mixed practice        ·  shuffle every available question", value="2"),
            questionary.Choice(
                f"Review wrong answers  ·  {len(wrong_dict)} question(s) on file",
                value="3",
                disabled=("no records" if not wrong_dict else False),
            ),
            questionary.Separator(),
            questionary.Choice("Quit", value="4"),
        ]

        choice = questionary.select(
            "Choose an action",
            choices=choices,
            use_indicator=False,
            qmark="▸",
            pointer="▸",
            style=Q_STYLE,
            instruction="(↑/↓ navigate · Enter select)",
        ).ask()

        if choice == '1':
            cat_choices = [
                questionary.Choice(
                    f"{cat:<28}  {sum(1 for q in all_questions if q['category'] == cat):>4} questions",
                    value=cat,
                )
                for cat in categories
            ]
            cat_choices.append(questionary.Separator())
            cat_choices.append(questionary.Choice("Back to dashboard", value="Q"))

            clear_screen()
            render_topbar()
            render_screen_header("Browse by category", "Select a subject to start a focused session")

            selected_cat = questionary.select(
                "Subject",
                choices=cat_choices,
                use_indicator=False,
                qmark="▸",
                pointer="▸",
                style=Q_STYLE,
            ).ask()

            if selected_cat and selected_cat != 'Q':
                cat_questions = [q for q in all_questions if q['category'] == selected_cat]
                run_quiz(cat_questions, wrong_dict, wrong_file_path, explanations)

        elif choice == '2':
            run_quiz(all_questions, wrong_dict, wrong_file_path, explanations)

        elif choice == '3':
            if wrong_dict:
                run_quiz(list(wrong_dict.values()), wrong_dict, wrong_file_path, explanations, is_review=True)

        elif choice == '4' or choice is None:
            clear_screen()
            render_topbar()
            console.print()
            console.print(Padding(Text("  Session ended. Good luck on the exam.", style=f"bold {C_PRIMARY}"), (1, 0)))
            console.print()
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print()
        console.print(Text("  Session interrupted.", style=f"bold {C_WARN}"))
        sys.exit(0)
