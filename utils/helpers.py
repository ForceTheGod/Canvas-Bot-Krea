from bs4 import BeautifulSoup

def clean_html(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def build_group_map(groups):
    return {g["id"]: g["name"] for g in groups} if groups else {}

def build_assignment_map(assignments):
    return {a["id"]: a for a in assignments} if assignments else {}

def categorize_with_assignments(submissions, assignment_map, group_map):
    categories = {}
    for s in submissions:
        score = s.get("score")
        if score is None:
            continue
        assignment_id = s.get("assignment_id")
        assignment = assignment_map.get(assignment_id)
        if not assignment:
            continue
        name = assignment.get("name", "Unnamed")
        max_score = assignment.get("points_possible", "?")
        group_id = assignment.get("assignment_group_id")
        group_name = group_map.get(group_id, "Other")
        entry = f"{name} → `{score}/{max_score}`"
        if group_name not in categories:
            categories[group_name] = []
        categories[group_name].append(entry)
    return categories

def trim_text(items, limit=1000):
    text = ""
    for item in items:
        if len(text) + len(item) + 1 > limit:
            break
        text += item + "\n"
    return text
