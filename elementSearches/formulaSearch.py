from .common import cached, store
from .formSearch import search as search_forms
from .lifecycleElementSearch import search as search_lifecycles
from .reportSearch import search as search_reports


LABEL = "Formula"


def search(client):
    """Preserve the original direct-use checks and formula-variable graph traversal."""
    if result := cached(client, "formula"):
        return result
    
    formulae, owners = {}, {}
    for object_type in client.object_types.get_all_obj_types():
        for formula in client.formulas.get_formulae_for_obj_type(obj_type_id=object_type.id):
            formulae[formula.id], owners[formula.id] = formula, object_type.id

    directly_used, locations = set(), {}

    def mark(formula_id, location): # Marks all locations where formula is us
        if formula_id in formulae:
            directly_used.add(formula_id)
            locations.setdefault(formula_id, set()).add(location)
    
    lifecycles, _ = search_lifecycles(client)
    transitions = {item["id"]: item for item in lifecycles["transitions"]}
    for formula_id, formula in formulae.items():
        transition_id = formula.transitionId
        if transition_id in transitions:
            mark(formula_id, f"Transition: {transitions[transition_id]['name']}")
    
    used_forms, _ = search_forms(client)
    for form in used_forms:
        for formula_id in client.forms.get_form_formula(form["id"]):
            mark(int(formula_id), f"Form: {form['name']}")

    used_reports, _ = search_reports(client)
    for report in used_reports:
        for component in client.reports.get_report_components(report["id"]):
            properties = component.dataProperties
            if component.subType == 4:
                for series in properties.series:
                    if series.xAxisType == 2:
                        mark(series.xValue, f"Report: {report['name']} → Component: {component.id}")
                    if series.yAxisType == 2:
                        mark(series.yValue, f"Report: {report['name']} → Component: {component.id}")
            elif component.subType in (2, 3, 5):
                for column in properties.columns:
                    if column.type == 3:
                        mark(column.identifier, f"Report: {report['name']} → Component: {component.id}")
    
    used_ids, stack = set(directly_used), list(directly_used)
    while stack:
        current_id = stack.pop()
        variables = client.formulas.get_formula_variables(obj_type_id=owners[current_id], formula_id=current_id)
        for variable in variables:
            formula_id = variable.targetFormulaId
            if formula_id in formulae:
                locations.setdefault(formula_id, set()).add(f"Variable for Formula: {formulae[current_id].name}")
                if formula_id not in used_ids:
                    used_ids.add(formula_id)
                    stack.append(formula_id)

    used = [{**formulae[formula_id].model_dump(), "Location(s)": " | ".join(sorted(locations.get(formula_id, [])))} for formula_id in used_ids]
    unused = [formula.model_dump() for formula_id, formula in formulae.items() if formula_id not in used_ids]
    return store(client, "formula", (used, unused))
