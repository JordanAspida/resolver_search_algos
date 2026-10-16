from .common import cached, get_object_types, get_formula_by_object_type, store
from .formSearch import search as search_forms
from .lifecycleElementSearch import search as search_lifecycles
from .reportSearch import search as search_reports


LABEL = "Formula"


def search(client):
    """Preserve the original direct-use checks and formula-variable graph traversal."""
    if result := cached(client, "formula"):
        return result
    formulae, owners = {}, {}
    for object_type in get_object_types(client):
        for formula in get_formula_by_object_type(client, object_type["id"]):
            formulae[formula["id"]], owners[formula["id"]] = formula, object_type["id"]
    directly_used, locations = set(), {}

    def mark(formula_id, location):
        if formula_id in formulae:
            directly_used.add(formula_id)
            locations.setdefault(formula_id, set()).add(location)

    lifecycles, _ = search_lifecycles(client)
    transitions = {item["id"]: item for item in lifecycles["transitions"]}
    for formula_id, formula in formulae.items():
        transition_id = formula.get("transitionId")
        if transition_id in transitions:
            mark(formula_id, f"Transition: {transitions[transition_id]['name']}")
    used_forms, _ = search_forms(client)
    for form in used_forms:
        for formula_id in client.forms.get_form_formula(form["id"]):
            mark(int(formula_id), f"Form: {form['name']}")
    used_reports, _ = search_reports(client)
    for report in used_reports:
        for component in client.reports.get_report_components(report["id"]):
            properties = component.get("dataProperties", {})
            if component.get("subtype") == 4:
                for series in properties.get("series", []):
                    if series.get("xAxisType") == 2:
                        mark(series.get("xValue"), f"Report: {report['name']} → Component: {component['id']}")
                    if series.get("yAxisType") == 2:
                        mark(series.get("yValue"), f"Report: {report['name']} → Component: {component['id']}")
            elif component.get("subtype") in (2, 3, 5):
                for column in properties.get("columns", []):
                    if column.get("type") == 3:
                        mark(column.get("identifier"), f"Report: {report['name']} → Component: {component['id']}")
    used_ids, stack = set(directly_used), list(directly_used)
    while stack:
        current_id = stack.pop()
        variables = client.safe_get(
            f"/object/objectType/{owners[current_id]}/formula/{current_id}/variable"
        ).get("data", [])
        for variable in variables:
            formula_id = variable.get("targetFormulaId")
            if formula_id in formulae:
                locations.setdefault(formula_id, set()).add(f"Variable for Formula: {formulae[current_id]['name']}")
                if formula_id not in used_ids:
                    used_ids.add(formula_id)
                    stack.append(formula_id)
    invalid = {item["id"] for item in client.safe_get("/object/formula/invalid").get("data", [])}
    used = [{**formulae[formula_id], "Location(s)": " | ".join(sorted(locations.get(formula_id, []))),
             "Invalid": "YES" if formula_id in invalid else "NO"} for formula_id in used_ids]
    unused = [formula for formula_id, formula in formulae.items() if formula_id not in used_ids]
    return store(client, "formula", (used, unused))
