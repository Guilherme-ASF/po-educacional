from __future__ import annotations

import re


def expand_summations(text: str) -> str:
    """Expande ∀, Σ e domínios indexados em restrições explícitas."""
    lines = text.splitlines()
    p_coefs: dict[tuple[str, str], float] = {}
    tasks: set[str] = set()
    servers: set[str] = set()
    cap: float | None = None

    for raw in lines:
        line = raw.strip()
        if line.startswith("#"):
            cap = _parse_comment(line, p_coefs, tasks, servers, cap)

    if not tasks or not servers:
        _infer_from_coefs(p_coefs, tasks, servers)
    if cap is None:
        cap = _find_cap_in_text(text)

    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            out.append(raw)
            continue

        if line.startswith("#") or re.match(r"^s\.?\s*a\.?\s*\.?$", line, re.I):
            out.append(raw)
            continue

        if not out and re.search(r"(max|min|z\s*=)", line, re.I):
            out.append(raw)
            continue

        if _is_indexed_domain(line):
            out.extend(_expand_domain(line, tasks, servers))
            continue

        expanded = _expand_line(line, p_coefs, tasks, servers, cap)
        if expanded:
            out.extend(expanded)
        else:
            out.append(raw)

    return "\n".join(out)


def _parse_comment(
    line: str,
    p_coefs: dict[tuple[str, str], float],
    tasks: set[str],
    servers: set[str],
    cap: float | None,
) -> float | None:
    for m in re.finditer(
        r"p\s*\[\s*([^,\]]+)\s*,\s*([^\]]+)\s*\]\s*=\s*(\d+(?:\.\d+)?)",
        line,
        re.I,
    ):
        t, s, v = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
        p_coefs[(t, s)] = v
        tasks.add(t)
        servers.add(s)

    cap_m = re.search(
        r"capacidade\s+c\s*=\s*(\d+(?:\.\d+)?)",
        line,
        re.I,
    )
    if not cap_m:
        cap_m = re.search(
            r"(?:capacidade|cap)\s*[=:]\s*(\d+(?:\.\d+)?)",
            line,
            re.I,
        )
    if not cap_m:
        cap_m = re.search(r"\bC\s*=\s*(\d+(?:\.\d+)?)", line)
    if cap_m:
        return float(cap_m.group(1))
    return cap


def _split_index_list(s: str) -> list[str]:
    return [x.strip() for x in re.split(r",\s*", s.strip()) if x.strip()]


def _expand_line(
    line: str,
    p_coefs: dict[tuple[str, str], float],
    tasks: set[str],
    servers: set[str],
    cap: float | None,
) -> list[str] | None:
    normalized = (
        line.replace("∑", "Σ")
        .replace("forall", "∀")
        .replace("for all", "∀")
        .replace("sum_", "Σ_")
        .replace("p(t,s)", "p[t,s]")
        .replace("p(t, s)", "p[t,s]")
        .replace("x[t,s]", "x_{t,s}")
        .replace("x[t, s]", "x_{t,s}")
    )

    m_assign = re.match(
        r"∀\s*t\s*∈\s*\{([^}]+)\}\s*:\s*Σ_?s\s*x_\{t,s\}\s*=\s*1",
        normalized,
        re.I,
    )
    if not m_assign:
        m_assign = re.match(
            r"∀\s*t\s*:\s*Σ_?s\s*x_\{t,s\}\s*=\s*1",
            normalized,
            re.I,
        )
        if m_assign:
            ts = sorted(tasks, key=_label_key) if tasks else []
            srvs = sorted(servers, key=_label_key)
            return [
                _join_terms([f"x_{t}_{s}" for s in srvs]) + " = 1"
                for t in ts
                if srvs
            ] or None
    if m_assign:
        ts = _split_index_list(m_assign.group(1))
        tasks.update(ts)
        srvs = sorted(servers, key=_label_key)
        return [
            _join_terms([f"x_{t}_{s}" for s in srvs]) + " = 1"
            for t in ts
            if srvs
        ] or None

    m_make = re.match(
        r"∀\s*s\s*∈\s*\{([^}]+)\}\s*:\s*Σ_?t\s*p\[t,s\]\s*[·*]\s*x_\{t,s\}\s*([<≤]=?)\s*M\s*$",
        normalized,
        re.I,
    )
    if not m_make:
        m_make = re.match(
            r"∀\s*s\s*:\s*Σ_?t\s*p\[t,s\]\s*[·*]\s*x_\{t,s\}\s*([<≤]=?)\s*M\s*$",
            normalized,
            re.I,
        )
        if m_make:
            srvs = sorted(servers, key=_label_key)
            return _load_constraints(srvs, tasks, p_coefs, "<=", "0", include_m=True)
    if m_make:
        srvs = _split_index_list(m_make.group(1))
        servers.update(srvs)
        return _load_constraints(srvs, tasks, p_coefs, "<=", "0", include_m=True)

    m_cap = re.match(
        r"∀\s*s\s*∈\s*\{([^}]+)\}\s*:\s*Σ_?t\s*p\[t,s\]\s*[·*]\s*x_\{t,s\}\s*([<≤]=?)\s*(\d+(?:\.\d+)?)\s*$",
        normalized,
        re.I,
    )
    if not m_cap:
        m_cap = re.match(
            r"∀\s*s\s*:\s*Σ_?t\s*p\[t,s\]\s*[·*]\s*x_\{t,s\}\s*([<≤]=?)\s*C\s*$",
            normalized,
            re.I,
        )
        if m_cap and cap is not None:
            srvs = sorted(servers, key=_label_key)
            return _load_constraints(srvs, tasks, p_coefs, "<=", str(cap), include_m=False)
    if m_cap:
        srvs = _split_index_list(m_cap.group(1))
        servers.update(srvs)
        rhs = m_cap.group(3)
        return _load_constraints(srvs, tasks, p_coefs, "<=", rhs, include_m=False)

    return None


def _load_constraints(
    srvs: list[str],
    tasks: set[str],
    p_coefs: dict[tuple[str, str], float],
    op: str,
    rhs: str,
    include_m: bool,
) -> list[str]:
    ts = sorted(tasks, key=_label_key)
    out: list[str] = []
    for s in srvs:
        terms: list[str] = []
        for t in ts:
            coef = p_coefs.get((t, s))
            if coef is None:
                continue
            vn = f"x_{t}_{s}"
            if coef == 1:
                terms.append(vn)
            elif coef == -1:
                terms.append(f"-{vn}")
            else:
                fc = int(coef) if coef == int(coef) else coef
                terms.append(f"{fc}{vn}")
        if not terms:
            continue
        if include_m:
            out.append(f"{_join_terms(terms + ['-M'])} {op} {rhs}")
        else:
            out.append(f"{_join_terms(terms)} {op} {rhs}")
    return out


def _is_indexed_domain(line: str) -> bool:
    return bool(
        re.search(r"x_\{t,s\}\s*(?:bin[aá]rio|inteiro)", line, re.I)
        or re.search(r"x_\{t,s\}\s*∈", line, re.I)
    )


def _expand_domain(line: str, tasks: set[str], servers: set[str]) -> list[str]:
    ts = sorted(tasks, key=_label_key)
    ss = sorted(servers, key=_label_key)
    names = [f"x_{t}_{s}" for t in ts for s in ss]
    kind = "binário" if re.search(r"bin", line, re.I) else "inteiro"
    return [", ".join(names) + f" {kind}"]


def _infer_from_coefs(
    p_coefs: dict[tuple[str, str], float],
    tasks: set[str],
    servers: set[str],
) -> None:
    for t, s in p_coefs:
        tasks.add(t)
        servers.add(s)


def _find_cap_in_text(text: str) -> float | None:
    m = re.search(r"capacidade\s*c\s*=\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        return float(m.group(1))
    return None


def _label_key(label: str) -> tuple[str, int]:
    m = re.match(r"([a-zA-Z]+)(\d+)", label)
    if m:
        return (m.group(1).lower(), int(m.group(2)))
    return (label.lower(), 0)


def _join_terms(terms: list[str]) -> str:
    if not terms:
        return "0"
    out = terms[0]
    for t in terms[1:]:
        if t.startswith("-"):
            out += f" - {t[1:]}"
        else:
            out += f" + {t}"
    return out
