from .common import cached, store
from .lifecycleElementSearch import search as search_lifecycles
from pydantic import ValidationError

import logging
logger = logging.getLogger(__name__)

LABEL = "Forms"


def search(client):
    """Find forms reachable through apps, reports, lifecycle actions, roles, and form links."""
    # Checks and returns cached result if it exists
    if result := cached(client, "forms"):
        return result

    # Retrieves all forms and creates a map of form id : form details
    forms = {form.id: form for form in client.forms.get_all_forms()}
    starting, paths = set(), {}

    # Sub-method for building paths
    def add(form_id, path):
        if form_id is not None:
            starting.add(form_id)
            paths.setdefault(form_id, set()).add(path)
    
    # Case 1: Forms used in apps
    logger.info("Searching for forms used in apps...")
    for app in client.applications.get_all_applications():
        for activity in client.applications.get_activities(app.id):
            for action in client.applications.get_actions(app.id, activity.id):
                if action.formId not in ("default", "", None):
                    add(action.formId, f"App: {app.name} → Activity: {activity.name} → Action: {action.name}")
            for view in client.applications.get_views(app.id, activity.id):
                if view.formId not in ("default", "", None):
                    add(view.formId, f"App: {app.name} → Activity: {activity.name} → View: {view.name}")
    
    # Case 2: Forms used in reports
    logger.info("Searching for forms used in reports...")
    for report in client.reports.get_all_reports():
        for component in client.reports.get_report_components(report.id):
            for form_id in component.dataProperties.forms.values():
                if form_id not in ("default", "", None):
                    add(form_id, f"Report: {report.name} ({report.id})")
    
    # Case 3: Forms used in lifecycle actions
    logger.info("Searching for forms used in lifecycle emailing actions...")
    lifecycles, _ = search_lifecycles(client)
    for action in client.lifecycle.post_state_actions([item["id"] for item in lifecycles["states"]], [1]):
        for transition in client.lifecycle.get_trigger_transitions(action.objectTypeId, action.objectLifeCycleId, action.triggerId):
            for detail in client.lifecycle.get_transition_actions(action.objectTypeId, action.objectLifeCycleId, transition.id):
                if detail.id == action.id:
                    add(detail.options.get("formId"), f"Lifecycle action: {detail.name}")
    
    # Case 4: Forms used in roles
    logger.info("Searching for forms used in roles...")
    roles = client.roles.get_all_roles()
    lifecycle_map = {item["id"]: item for item in lifecycles["lifecycles"]}
    for role in roles:
        logger.info(f"Searching Role: {role.name} ... ")
        records = client.roles.get_lifecycles_for_role(role_id=role.id)
        logger.info(f"Identified lifecycle ids: {records}")
        for record in records:
            lifecycle = lifecycle_map.get(record.objectLifeCycleId)
            if lifecycle is None:
                continue
            permissions = client.roles.get_obj_permissions_for_role(object_type_id=lifecycle["objectTypeId"], role_id=role.id)
            for permission in permissions:
                if permission.formId is not None:
                    add(permission.formId, f"Role: {role.name} → Lifecycle: {lifecycle["name"]}")
    
    # Case 5: Forms linked in other used forms
    logger.info("Searching for forms linked through other forms...")
    used_ids, stack = set(starting), list(starting) # Initialise a stack with starting form ids for depth-first traversal
    while stack:
        form_id = stack.pop() # Removes top element in the stack and assigns it to form_id
        logger.info(f"Searching for linked forms for form id: {form_id} ...")
        form = forms.get(form_id)
        if form is None:
            continue
        if form.type == 1: # if standard form
            try:
                linked, components = client.forms.get_linked_forms(form_id, comps=True) # Retrieves all linked forms and form components (to check if scoping forms linked)
                linked_ids = [item.id for item in linked]
                linked_ids += [item.dataProperties.get("formId") for item in components if item.type == 11] # Adds scoping forms if present
            except ValidationError as e:
                logger.warning(f"Validation error while retrieving linked forms for form id: {form_id}. Error: {e}")
                continue
            
        elif form.type == 2: # if nav form
            try:
                nav_form_struct = client.forms.get_all_forms_in_nav_form(form_id)
                linked_ids = []
                for item in nav_form_struct:
                    if item.formId is not None:
                        linked_ids.append(item.formId)
                    if item.stateConfig not in (None, []):
                        linked_ids += [state.formId for state in item.stateConfig if state.formId is not None] # Adds state specific forms if present
            except ValidationError as e:
                logger.warning(f"Validation error while retrieving nav form structure for form id: {form_id}. Error: {e}")
                continue
        else:
            logger.warning(f"Skipping unrecognised form type {form.type} for form id: {form_id}")
            continue
        for linked_id in linked_ids:
            if linked_id is not None:
                paths.setdefault(linked_id, set()).update(paths.get(form_id, set())) # build path
                if linked_id not in used_ids: # if the form has not been found elsewhere add to the stack so that it is checked for any linked forms too
                    used_ids.add(linked_id)
                    stack.append(linked_id)

    used = [{**forms[form_id].model_dump(), "path": " | ".join(sorted(paths.get(form_id, [])))}
            for form_id in used_ids if form_id in forms] # Format all used forms with their paths so that they can be uploaded appropriately to an excel sheet
    unused = [form.model_dump() for form_id, form in forms.items() if form_id not in used_ids] # Format unused forms so they can be uploaded properly
    return store(client, "forms", (used, unused))
