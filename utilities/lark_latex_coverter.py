'''
Created on Jul 26, 2026

@author: haris
'''

#!/usr/bin/env python3

import re
from pathlib import Path


def latex_escape(text):
    """Escape LaTeX special characters."""
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "$": r"\$",
        "^": r"\^{}",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text


def convert_rhs(rhs):

    rhs = rhs.strip()

    # remove comments
    rhs = re.sub(r"//.*", "", rhs)

    # terminals in quotes
    rhs = re.sub(
        r'"([^"]*)"',
        lambda m: r"\texttt{" + latex_escape(m.group(1)) + "}",
        rhs,
    )

    # Lark aliases
    rhs = re.sub(r"\s*->\s*\w+", "", rhs)

    # optional
    rhs = rhs.replace("?", r"$^{?}$")

    # zero or more
    rhs = rhs.replace("*", r"$^{*}$")

    # one or more
    rhs = rhs.replace("+", r"$^{+}$")

    # alternation
    rhs = rhs.replace("|", r"\textbar{}")

    return rhs.strip()


def parse_lark(filename):

    productions = []

    with open(filename) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            if line.startswith("%"):
                continue

            if line.startswith("//"):
                continue

            if ":" not in line:
                continue

            lhs, rhs = line.split(":", 1)

            productions.append((lhs.strip(), convert_rhs(rhs)))

    return productions


def generate_table(productions):

    out = []

    out.append(r"\begingroup")
    out.append(r"\renewcommand{\arraystretch}{0.92}")
    out.append(r"\setlength{\tabcolsep}{4pt}")

    out.append(r"\begin{longtable}{")
    out.append(r">{\ttfamily\small}p{0.28\textwidth}")
    out.append(r">{\raggedright\arraybackslash\small}p{0.66\textwidth}")
    out.append(r"}")

    out.append(r"\caption{Grammar}")
    out.append(r"\label{tab:grammar}\\")
    out.append(r"\toprule")
    out.append(r"\textbf{Nonterminal} & \textbf{Production Rule}\\")
    out.append(r"\midrule")
    out.append(r"\endfirsthead")

    out.append(r"\toprule")
    out.append(r"\textbf{Nonterminal} & \textbf{Production Rule}\\")
    out.append(r"\midrule")
    out.append(r"\endhead")

    out.append(r"\bottomrule")
    out.append(r"\endfoot")

    for lhs, rhs in productions:

        parts = [x.strip() for x in rhs.split(r"\textbar{}")]

        out.append(
            f"{latex_escape(lhs)} & ::= {parts[0]}\\\\"
        )

        for p in parts[1:]:
            out.append(
                f"& \\textbar{{}} {p}\\\\"
            )

        out.append("")

    out.append(r"\end{longtable}")
    out.append(r"\endgroup")

    return "\n".join(out)


if __name__ == "__main__":

    GRAMMAR_PATH = (
        Path(__file__)
        .parent
        .parent
        / "grammar"
        / "process1.lark")

    grammar = parse_lark(GRAMMAR_PATH)

    tex = generate_table(grammar)

    Path("grammar.tex").write_text(tex)

    print("Written grammar.tex")